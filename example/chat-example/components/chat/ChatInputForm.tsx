"use client";

import { useChat } from "@/hooks/useChat";
import { useCommandInput } from "@/hooks/useCommandInput";
import { authAtom } from "@/store/authAtom";
import { useAtomValue } from "jotai";
import { useEffect, useRef } from "react";

const ChatInputForm = () => {
  const { changeRoom, createRoom, sendNotice, sendMessage } = useChat();
  const { id } = useAtomValue(authAtom);

  const { command, controls, resetCommand } = useCommandInput({
    "/c": (roomId) => createRoom(roomId),
    "/j": (roomId) => changeRoom(roomId),
    "/n": (message) =>
      sendNotice({
        message,
        user_id: id,
      }),
  });
  const textRef = useRef<HTMLTextAreaElement>(null);

  const onSubmit = (e?: React.FormEvent<HTMLFormElement>) =>
    controls.form.onSubmit(e, () => {
      console.log(id, controls.message.value);
      sendMessage({
        message: controls.message.value,
        user_id: id,
      });
    });

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter 키를 눌렀을 때 줄바꿈이 되는 것을 방지하기 위해 먼저 개행 이벤트를 막는다.
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
    }
  };

  const onKeyUp = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter 키를 떼었을 때 메시지를 전송한다.
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSubmit();
    }

    if (e.key === "Backspace" && controls.message.value === "") {
      resetCommand();
    }
  };

  useEffect(() => {
    if (textRef) {
      textRef.current?.focus();
    }
  }, [command]);

  return (
    <form className="form-control w-full" onSubmit={onSubmit}>
      <div className="join w-full">
        {command ? (
          <button
            className="btn btn-info join-item h-auto"
            onClick={resetCommand}
          >
            {command}
          </button>
        ) : null}
        <textarea
          className="textarea textarea-bordered join-item basis-4/5 focus:outline-none"
          placeholder="Type a message"
          rows={1}
          ref={textRef}
          onKeyDown={onKeyDown}
          onKeyUp={onKeyUp}
          {...controls.message}
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
