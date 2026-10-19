// 비서실이 직접 만든 결과물을 담당 팀 이름으로 스튜디오 결재(확인만 하면 끝나는 보고)로 올려 자료실에 쌓는다.
// 사용: node archive.mjs manifest.json   (manifest: [{staffId, title, body, topic, files:[절대경로]}])
import { initializeApp } from 'firebase/app';
import { getAuth, signInWithEmailAndPassword } from 'firebase/auth';
import { getFirestore, doc, setDoc } from 'firebase/firestore';
import { getStorage, ref as sref, uploadBytes, getDownloadURL } from 'firebase/storage';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { basename } from 'node:path';
const EMAIL = 'studio-bridge@vinfilmstudio.com';
const app = initializeApp({ apiKey: 'AIzaSyAVJ6ZZ6L-3RtgoYe2dDSn_lCHXv3CeBGc', authDomain: 'vinfilm-studio-app.firebaseapp.com', projectId: 'vinfilm-studio-app', storageBucket: 'vinfilm-studio-app.firebasestorage.app' });
const MIME = { pdf: 'application/pdf', png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', webp: 'image/webp', md: 'text/markdown; charset=utf-8', txt: 'text/plain; charset=utf-8', csv: 'text/csv; charset=utf-8', mp4: 'video/mp4' };
const pw = execFileSync('security', ['find-generic-password', '-s', 'vinfilm-studio-bridge', '-a', EMAIL, '-w'], { encoding: 'utf8' }).trim();
await signInWithEmailAndPassword(getAuth(app), EMAIL, pw);
const db = getFirestore(app), st = getStorage(app);
for (const it of JSON.parse(readFileSync(process.argv[2], 'utf8'))) {
  const id = 'a' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  const files = [];
  for (const p of it.files) {
    const name = basename(p), ext = (name.split('.').pop() || '').toLowerCase();
    const r = sref(st, `studio/${id}/${name}`);
    await uploadBytes(r, readFileSync(p), MIME[ext] ? { contentType: MIME[ext] } : undefined);
    files.push({ name, url: await getDownloadURL(r) });
  }
  await setDoc(doc(db, 'studioApprovals', id), { id, from: it.staffId, staffId: it.staffId, taskId: '', title: it.title, body: it.body, files, actions: [], choices: [], followUp: false, topic: it.topic, by: 'sec-direct', status: 'wait', createdAt: Date.now() });
  console.log('OK', it.staffId, id, files.length);
}
process.exit(0);
