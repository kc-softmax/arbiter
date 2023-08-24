"use client";

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
  const setAuthInfo = useSetAtom(authAtom);

  const requestSignUp = async () => {
    const body = {
      email: id,
      password,
    };

    const response = await fetch(
      `${process.env.NEXT_PUBLIC_HOST}/auth/game/signup/email`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      }
    );

    if (!response.ok) return alert("Sign In Failed");

    const data = await response.json();

    console.log("signUp :>> ", data);
  };

  const updateUserInfo = async (token: string) => {
    const body = {
      user_name: id.split("@")[0],
    };

    const response = await fetch(
      `${process.env.NEXT_PUBLIC_HOST}/auth/game/me`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      }
    );

    if (!response.ok) return alert("Update User Info Failed");
  };

  const requestLogin = async () => {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_HOST}/auth/game/login/email`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: `username=${id}&password=${password}`,
      }
    );

    if (!response.ok) return alert("Login Failed");

    const data: { access_token: string; refresh_token: string } =
      await response.json();

    return data;
  };

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!id || !password) return alert("Please enter your name");

    if (isSignUp) {
      await requestSignUp();
    }

    const tokens = await requestLogin();

    if (!tokens) return;

    const { access_token } = tokens;

    const payload = access_token.split(".")[1];
    const { sub } = JSON.parse(atob(payload)) as {
      sub: string;
    };

    setAuthInfo({ id: sub, token: access_token });

    await updateUserInfo(access_token);

    next();
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
              Start Chat
            </button>
          </div>
        </form>
      </div>
    </section>
  );
};

export default StartChatPanel;
