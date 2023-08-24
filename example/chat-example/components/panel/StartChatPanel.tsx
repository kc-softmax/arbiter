"use client";

import { requestLogin, requestSignUp, updateUserInfo } from "@/api/auth";
import { authAtom } from "@/store/authAtom";
import { useSetAtom } from "jotai";
import React, { useState } from "react";

interface StartChatPanelProps {
  next: () => void;
}

const StartChatPanel = ({ next }: StartChatPanelProps) => {
  const [id, setID] = useState(
    process.env.NODE_ENV === "development" ? "@admin.com" : ""
  );
  const [password, setPassword] = useState(
    process.env.NODE_ENV === "development" ? "password" : ""
  );
  const [isSignUp, setIsSignUp] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const setAuthInfo = useSetAtom(authAtom);

  const getIdFromToken = (token: string) => {
    const payload = token.split(".")[1];
    const { sub } = JSON.parse(atob(payload)) as {
      sub: string;
    };

    return sub;
  };

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!id || !password) return alert("Please enter your ID and password");

    try {
      if (isSignUp) {
        setStatusMessage("Signing Up...");
        await requestSignUp({ id, password });
      }

      setStatusMessage("Logging In...");
      const tokens = await requestLogin({ id, password });

      const { access_token } = tokens;

      const idFromToken = getIdFromToken(access_token);

      setAuthInfo({ id: idFromToken, token: access_token });

      setStatusMessage("Updating User Info...");
      await updateUserInfo({
        id,
        token: access_token,
      });

      setStatusMessage("Done!");
      next();
    } catch (error) {
      if (error instanceof Error) {
        alert(error.message);
      }
    }
  };

  return (
    <section>
      <div>
        <form
          className="flex h-screen justify-center items-center"
          onSubmit={onSubmit}
        >
          <div className="border p-4 flex flex-col gap-4 rounded-md">
            <div className="tabs tabs-boxed">
              <a
                className={`tab basis-1/2 ${isSignUp ? "" : "tab-active"}`}
                onClick={() => setIsSignUp(false)}
              >
                Login
              </a>
              <a
                className={`tab basis-1/2 ${isSignUp ? "tab-active" : ""}`}
                onClick={() => setIsSignUp(true)}
              >
                Sign In
              </a>
            </div>
            <div className="join join-vertical">
              <input
                type="text"
                className="input input-bordered input-lg join-item"
                placeholder="Type Your Name"
                onChange={(e) => setID(e.target.value)}
                value={id}
              />
              <input
                type="password"
                className="input input-bordered input-lg join-item"
                placeholder="Type Your password"
                onChange={(e) => setPassword(e.target.value)}
                value={password}
              />
            </div>
            <button type="submit" className="btn btn-primary btn-lg w-auto">
              {statusMessage || "Start Chat"}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
};

export default StartChatPanel;
