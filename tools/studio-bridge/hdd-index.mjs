// HDD 보관 목록 올리기: node hdd-index.mjs <hddIndex.json>
// JSON = { serial:'EQ-081', name, totalGB, usedGB, freeGB, otherGB, otherNote, folders:[{name, top, gb, videos, first, last, thumb}] }
// 장비목록에서 serial이 같은 장비를 찾아 Firestore hddIndex/{장비 id}에 적는다 (규칙: 대표님·스튜디오 직원 계정만).
import { initializeApp } from 'firebase/app';
import { getAuth, signInWithEmailAndPassword } from 'firebase/auth';
import { getFirestore, collection, query, where, getDocs, doc, setDoc } from 'firebase/firestore';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';

const EMAIL = 'studio-bridge@vinfilmstudio.com';
const app = initializeApp({ apiKey: 'AIzaSyAVJ6ZZ6L-3RtgoYe2dDSn_lCHXv3CeBGc', authDomain: 'vinfilm-studio-app.firebaseapp.com', projectId: 'vinfilm-studio-app' });
const pw = execFileSync('security', ['find-generic-password', '-s', 'vinfilm-studio-bridge', '-a', EMAIL, '-w'], { encoding: 'utf8' }).trim();
await signInWithEmailAndPassword(getAuth(app), EMAIL, pw);
const db = getFirestore(app);
const data = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const snap = await getDocs(query(collection(db, 'equipment'), where('serial', '==', data.serial)));
if (snap.empty) { console.error('장비를 못 찾음', data.serial); process.exit(1); }
const eq = snap.docs[0];
await setDoc(doc(db, 'hddIndex', eq.id), { ...data, eqId: eq.id, scannedAt: Date.now() });
console.log('OK', data.serial, eq.data().name, eq.id, data.folders.length + '개 폴더');
process.exit(0);
