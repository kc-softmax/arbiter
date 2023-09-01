"use client";

import { useChat } from "@/hooks/useChat";
import { useCommandInput } from "@/hooks/useCommandInput";
import { authAtom } from "@/store/authAtom";
import { chatAtom, chatSetWhisperTargetAtom } from "@/store/chatAtom";
import { useAtomValue, useSetAtom } from "jotai";
import { useEffect, useRef } from "react";

const ChatInputForm = () => {
  const {
    changeRoom,
    createRoom,
    sendNotice,
    sendMessage,
    sendWhisper,
    inviteUser,
  } = useChat();
  const { id } = useAtomValue(authAtom);

  const { whisperTarget } = useAtomValue(chatAtom);
  const setWhisperTarget = useSetAtom(chatSetWhisperTargetAtom);

  const {
    commands,
    command,
    controls,
    reset,
    resetCommand,
    components: { CommandAutoComplete },
  } = useCommandInput({
    "/c": {
      name: "create",
      action: (roomId) => {
        createRoom(roomId);
        changeRoom(roomId);
      },
    },
    "/j": {
      name: "join",
      action: (roomId) => changeRoom(roomId),
    },
    "/n": {
      name: "notice",
      action: (message) => sendNotice(message),
    },
    "/i": {
      name: "invite",
      action: (userId) => {
        inviteUser({
          userTo: userId,
          userFrom: id,
        });
      },
    },
    "/w": {
      name: "whisper",
      action: (userId) => {
        setWhisperTarget(userId);
      },
    },
  });
  const textRef = useRef<HTMLTextAreaElement>(null);

  const onSubmit = (e?: React.FormEvent<HTMLFormElement>) => {
    if (whisperTarget) {
      sendWhisper({
        message: controls.message.value,
        userId: id,
        whisperTarget,
      });
      reset();
      return;
    }

    controls.form.onSubmit(e, () => {
      console.log(id, controls.message.value);
      sendMessage(controls.message.value);
    });
  };

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
      setWhisperTarget(null);
    }
  };

  useEffect(() => {
    if (textRef) {
      textRef.current?.focus();
    }
  }, [command, whisperTarget]);

  return (
    <form className="form-control w-full" onSubmit={onSubmit}>
      <CommandAutoComplete />

      <div className="join w-full">
        {command ? (
          <button
            className="btn btn-info join-item h-auto"
            onClick={resetCommand}
          >
            {commands[command].name}
          </button>
        ) : null}
        {whisperTarget ? (
          <button
            className="btn btn-info join-item h-auto"
            onClick={() => setWhisperTarget(null)}
          >
            TO: {whisperTarget}
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
