/**
 * VINFILM 캘린더 자동 동기화 (Google Apps Script)
 * 작업관리 앱(Firestore "schedule")의 일정을 10분마다 Google 캘린더 "VINFILM STUDIO"(촬영·미팅·답사)와
 * "VINFILM 작업"(마감·기타)에 맞춰 넣는다 — 앱을 안 열어도, 앱의 1시간 권한이 끝나도 계속 돈다.
 *
 * 앱 안 동기화(works/index.html gcalPush)와 똑같은 규칙을 쓴다: 이벤트 id = "vf" + 일정 id의 16진수,
 * 같은 내용·같은 캘린더 배치 → 둘이 같이 돌아도 일정이 두 번 생기지 않는다. 앱이 만든 vf… 일정만 고치고 지우며,
 * 대표님이 캘린더에 직접 넣은 일정은 건드리지 않는다.
 *
 * 처음 한 번: setup() 실행 → 권한 허용. 그 뒤로는 10분마다 syncNow()가 자동으로 돈다.
 */
var PROJECT_ID = 'vinfilm-studio-app';
var CAL_SHARE = 'VINFILM STUDIO';
var CAL_WORK = 'VINFILM 작업';
var SHARE_CATS = ['shoot', 'meeting', 'scout'];
var CAT_LABEL = { shoot: '촬영', meeting: '미팅', scout: '답사', deadline: '마감', etc: '기타' };
var TZ = 'Asia/Seoul';

function setup() {
  ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'syncNow') ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('syncNow').timeBased().everyMinutes(10).create();
  CalendarApp.getDefaultCalendar(); // 캘린더 권한을 같이 받기 위한 줄
  syncNow();
  Logger.log('설정 완료 — 10분마다 자동 동기화됩니다.');
}

function syncNow() {
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) return;
  try {
    var items = readSchedule_();
    var calShare = findCalendar_(CAL_SHARE), calWork = findCalendar_(CAL_WORK);
    if (!calShare || !calWork) throw new Error('VINFILM 캘린더를 찾지 못했어요 — 앱에서 휴대폰 캘린더 연결을 먼저 한 번 해 주세요.');
    var want = {}; // 캘린더id|이벤트id → body
    items.forEach(function (it) {
      if (it.source === 'calendar' || !it.date) return;
      var cal = SHARE_CATS.indexOf(it.category) >= 0 ? calShare : calWork;
      var body = bodyFor_(it);
      want[cal + '|' + body.id] = { cal: cal, body: body };
    });
    var existing = {};
    [calShare, calWork].forEach(function (cal) {
      listEvents_(cal).forEach(function (ev) { if (ev.id && ev.id.indexOf('vf') === 0) existing[cal + '|' + ev.id] = ev; });
    });
    var put = 0, del = 0;
    Object.keys(want).forEach(function (k) {
      var w = want[k], ev = existing[k];
      if (ev && same_(ev, w.body)) return;
      var base = '/calendars/' + encodeURIComponent(w.cal) + '/events';
      var r = api_('put', base + '/' + w.body.id, w.body, true);
      if (r === 404) api_('post', base, w.body);
      put++;
    });
    // 지울 일정: 앱에서 지웠거나 다른 캘린더로 옮겨간 vf… 일정. 데이터를 덜 읽어 온 경우 대량 삭제를 막는 안전장치.
    var gone = Object.keys(existing).filter(function (k) { return !want[k]; });
    if (gone.length > 10 && gone.length > Object.keys(existing).length / 2) {
      Logger.log('지울 일정이 너무 많아서(' + gone.length + '개) 이번에는 지우지 않았어요. 확인이 필요해요.');
    } else {
      gone.forEach(function (k) {
        var cal = k.split('|')[0], id = k.split('|')[1];
        api_('delete', '/calendars/' + encodeURIComponent(cal) + '/events/' + id, null, true);
        del++;
      });
    }
    Logger.log('동기화 완료: 일정 ' + Object.keys(want).length + '개, 고침 ' + put + ', 지움 ' + del);
  } finally {
    lock.releaseLock();
  }
}

/* ---------- 앱과 같은 이벤트 모양 ---------- */
function eventIdFor_(id) { var s = String(id), h = ''; for (var i = 0; i < s.length; i++) h += ('0' + s.charCodeAt(i).toString(16)).slice(-2); return 'vf' + h; }
function addDays_(ymd, n) { var p = ymd.split('-').map(Number); var d = new Date(p[0], p[1] - 1, p[2] + n); return Utilities.formatDate(d, TZ, 'yyyy-MM-dd'); }
function pad_(n) { return ('0' + n).slice(-2); }
function bodyFor_(it) {
  var desc = [it.memo || '', it.contact ? '연락처: ' + it.contact : '', CAT_LABEL[it.category] ? '분류: ' + CAT_LABEL[it.category] : ''].filter(String).join('\n');
  var b = { id: eventIdFor_(it.id), summary: it.title || '', location: it.location || '', description: desc, status: 'confirmed', extendedProperties: { private: { vfId: String(it.id) } } };
  var multi = it.endDate && it.endDate > it.date;
  if (it.time) {
    var hm = it.time.split(':').map(Number), h = hm[0], m = hm[1];
    var endH = pad_(Math.min(h + 1, 23)), endM = h + 1 > 23 ? '59' : pad_(m);
    b.start = { dateTime: it.date + 'T' + it.time + ':00', timeZone: TZ };
    b.end = { dateTime: (multi ? it.endDate : it.date) + 'T' + endH + ':' + endM + ':00', timeZone: TZ };
  } else {
    b.start = { date: it.date };
    b.end = { date: addDays_(multi ? it.endDate : it.date, 1) };
  }
  return b;
}
function norm_(t) { // Google이 돌려주는 시각(+09:00 포함)과 우리 값을 같은 모양으로
  if (!t) return '';
  if (t.date) return 'D' + t.date;
  return 'T' + String(t.dateTime).slice(0, 19);
}
function same_(ev, b) {
  return (ev.summary || '') === b.summary && (ev.location || '') === b.location && (ev.description || '') === b.description &&
    norm_(ev.start) === norm_(b.start) && norm_(ev.end) === norm_(b.end);
}

/* ---------- Firestore 읽기 (대표님 계정 권한으로, 읽기만) ---------- */
function readSchedule_() {
  var out = [], token = '';
  do {
    var url = 'https://firestore.googleapis.com/v1/projects/' + PROJECT_ID + '/databases/(default)/documents/schedule?pageSize=300' + (token ? '&pageToken=' + encodeURIComponent(token) : '');
    var res = UrlFetchApp.fetch(url, { headers: authHeaders_(), muteHttpExceptions: true });
    if (res.getResponseCode() !== 200) throw new Error('Firestore 읽기 실패 ' + res.getResponseCode() + ': ' + res.getContentText().slice(0, 300));
    var data = JSON.parse(res.getContentText());
    (data.documents || []).forEach(function (d) { var o = fsObj_(d.fields || {}); if (o.id == null) o.id = d.name.split('/').pop(); out.push(o); });
    token = data.nextPageToken || '';
  } while (token);
  return out;
}
function fsVal_(v) {
  if (v == null) return null;
  if ('stringValue' in v) return v.stringValue;
  if ('integerValue' in v) return Number(v.integerValue);
  if ('doubleValue' in v) return v.doubleValue;
  if ('booleanValue' in v) return v.booleanValue;
  if ('nullValue' in v) return null;
  if ('timestampValue' in v) return v.timestampValue;
  if ('mapValue' in v) return fsObj_(v.mapValue.fields || {});
  if ('arrayValue' in v) return (v.arrayValue.values || []).map(fsVal_);
  return null;
}
function fsObj_(f) { var o = {}; Object.keys(f).forEach(function (k) { o[k] = fsVal_(f[k]); }); return o; }

/* ---------- Google 캘린더 API ---------- */
function authHeaders_() { return { Authorization: 'Bearer ' + ScriptApp.getOAuthToken(), 'X-Goog-User-Project': PROJECT_ID }; }
function api_(method, path, body, allow404) {
  var opt = { method: method, headers: authHeaders_(), muteHttpExceptions: true }; // VINFILM 프로젝트(캘린더 API 켜져 있음)로 요청
  if (body) { opt.contentType = 'application/json'; opt.payload = JSON.stringify(body); }
  var res = UrlFetchApp.fetch('https://www.googleapis.com/calendar/v3' + path, opt);
  var code = res.getResponseCode();
  if (allow404 && (code === 404 || code === 410)) return 404;
  if (code >= 300) throw new Error('캘린더 ' + method + ' 실패 ' + code + ': ' + res.getContentText().slice(0, 300));
  return code === 204 ? null : JSON.parse(res.getContentText() || 'null');
}
function findCalendar_(name) {
  var r = api_('get', '/users/me/calendarList?maxResults=250');
  var c = (r.items || []).filter(function (x) { return x.summary === name && x.accessRole === 'owner'; })[0];
  return c ? c.id : null;
}
function listEvents_(cal) {
  var out = [], token = '';
  do {
    var r = api_('get', '/calendars/' + encodeURIComponent(cal) + '/events?maxResults=2500&showDeleted=false' + (token ? '&pageToken=' + encodeURIComponent(token) : ''));
    out = out.concat(r.items || []); token = r.nextPageToken || '';
  } while (token);
  return out;
}
