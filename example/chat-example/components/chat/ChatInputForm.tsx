"use client";

import { useEffect, useRef, useState } from "react";

interface ChatInputFormProps {
  sendChat: (message: string) => void;
}

const ChatInputForm = ({ sendChat }: ChatInputFormProps) => {
  const [message, setMessage] = useState("");
  const textRef = useRef<HTMLTextAreaElement>(null);

  const onSubmit = (e?: React.FormEvent<HTMLFormElement>) => {
    e?.preventDefault();

    if (message.trim() === "") {
      return;
    }

    sendChat(message);
    setMessage("");
    textRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      textRef.current?.blur();
      onSubmit();
    }
  };

  useEffect(() => {
    if (textRef) {
      textRef.current?.focus();
    }
  }, [textRef]);

  return (
    <form className="form-control w-full" onSubmit={onSubmit}>
      <div className="join w-full">
        <textarea
          className="textarea textarea-bordered join-item basis-4/5"
          placeholder="Type a message"
          ref={textRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
        ></textarea>
        <button
          type="submit"
          className="btn btn-primary join-item basis-1/5 h-auto"
        >
          Send
        </button>
      </div>
    </form>
  );
};

export default ChatInputForm;
