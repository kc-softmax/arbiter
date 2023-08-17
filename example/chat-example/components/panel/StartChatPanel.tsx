"use client";

import { ChatInfo } from "@/@types/chat";
import React, { useState } from "react";

interface StartChatPanelProps {
  next: (chatInfo: ChatInfo) => void;
}

const StartChatPanel = ({ next }: StartChatPanelProps) => {
  const [id, setID] = useState("");
  const [password, setPassword] = useState("");

  const requestLogin = async () => {
    const response = await fetch(
      "http://192.168.0.48:8880/auth/console/login",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: `username=${id}&password=${password}`,
      }
    );

    const data: { access_token: string; refresh_token: string } =
      await response.json();

    return data;
  };

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!id || !password) return alert("Please enter your name");

    const { access_token } = await requestLogin();

    // TODO: 진짜 id로 바꿀 예정
    next({ token: access_token, id: id.split("@")[0] });
  };

  return (
    <section>
      <div>
        <form
          className="flex h-screen justify-center items-center"
          onSubmit={onSubmit}
        >
          <div className="border p-4 flex flex-col gap-4 rounded-md">
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
