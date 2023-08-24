import { AuthInfo } from "@/@types/chat";
import { atom } from "jotai";

export const authAtom = atom<AuthInfo>({
  id: "",
  token: "",
});
