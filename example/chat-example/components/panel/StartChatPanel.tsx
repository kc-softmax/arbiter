"use client";

import React, { useState } from "react";

interface StartChatPanelProps {
  next: (name: string) => void;
}

const StartChatPanel = ({ next }: StartChatPanelProps) => {
  const [name, setName] = useState("");

  const onSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!name) return alert("Please enter your name");

    next(name);
  };

  return (
    <section>
      <div>
        <form
          className="flex h-screen justify-center items-center join"
          onSubmit={onSubmit}
        >
          <input
            type="text"
            className="input input-bordered input-lg join-item"
            placeholder="Type Your Name"
            onChange={(e) => setName(e.target.value)}
            value={name}
          />
          <button type="submit" className="btn btn-primary btn-lg join-item">
            Start Chat
          </button>
        </form>
      </div>
    </section>
  );
};

export default StartChatPanel;
