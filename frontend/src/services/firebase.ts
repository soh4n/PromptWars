/** Firebase client SDK initialisation. */
import { initializeApp } from "firebase/app";
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  sendPasswordResetEmail,
  updateProfile,
  signOut as firebaseSignOut,
  onAuthStateChanged,
  type User,
} from "firebase/auth";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "AIzaSyBQaAVoaLlrgL1eXQDL-KZP4o46k9Ab27U",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "promptwars-494401.firebaseapp.com",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "promptwars-494401",
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || "promptwars-494401.firebasestorage.app",
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "596074253382",
  appId: import.meta.env.VITE_FIREBASE_APP_ID || "1:596074253382:web:48d4a32a1ac7137a7e0e47",
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const googleProvider = new GoogleAuthProvider();

export {
  auth,
  googleProvider,
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  sendPasswordResetEmail,
  updateProfile,
  firebaseSignOut,
  onAuthStateChanged,
};
export type { User };
