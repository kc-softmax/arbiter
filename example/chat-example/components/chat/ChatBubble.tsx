import { ChatMessage } from "@/@types/chat";
import { useChat } from "@/hooks/useChat";
import { authAtom } from "@/store/authAtom";
import { useAtomValue } from "jotai";
import { useState } from "react";
import ChatLinkPreview from "./ChatLinkPreview";

interface ChatBubbleProps {
  message: ChatMessage;
}

const ChatBubble = ({ message }: ChatBubbleProps) => {
  const { sendNotice } = useChat();
  const [isReported, setIsReported] = useState(false);
  const { id } = useAtomValue(authAtom);
  const {
    message: messageText,
    message_id,
    time,
    user: { user_id: userId, user_name: username },
  } = message;

  const onClickNotice = () => {
    sendNotice(messageText, userId.toString());
  };

  const onClickReport = () => {
    alert(`Reported: ${userId}-${username}'s ${messageText}`);
    setIsReported(true);
  };

  const onClickGood = () => {
    console.log("good", message_id);
  };

  const onClickBad = () => {
    console.log("bad", message_id);
  };

  const isMe = id === userId.toString();

  return (
    <div className={`chat ${isMe ? "chat-end" : "chat-start"}`}>
      <p className="chat-header">{username}</p>
      <div
        tabIndex={0}
        className={`dropdown dropdown-hover chat-bubble flex justify-center items-end cursor-pointer max-w-[70%] ${
          isMe
            ? "chat-bubble-primary dropdown-left"
            : "chat-bubble-secondary dropdown-right"
        }`}
      >
        {isReported ? <p>Reported 🚨</p> : <p>{messageText}</p>}

        <div
          tabIndex={0}
          className="dropdown-content z-20 p-2 shadow bg-base-100 rounded-box space-y-2"
        >
          <button
            className="btn btn-warning btn-outline btn-block"
            onClick={onClickNotice}
          >
            Notice
          </button>
          <button
            className="btn btn-error btn-outline btn-block"
            onClick={onClickReport}
          >
            Report
          </button>
          <div className="join w-full">
            <button
              className="join-item flex-1 btn btn-outline btn-sm btn-success"
              onClick={onClickGood}
            >
              👍
            </button>
            <button
              className="join-item flex-1 btn btn-outline btn-sm btn-error"
              onClick={onClickBad}
            >
              👎
            </button>
          </div>
        </div>
      </div>
      <time className="chat-footer opacity-50">
        {new Date(time).toLocaleString()}
      </time>
      <ChatLinkPreview messageText={messageText} />
    </div>
  );
};

export default ChatBubble;
