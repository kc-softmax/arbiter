"use client";

import { requestUserInfo } from "@/api/auth";
import { useChat } from "@/hooks/useChat";
import { authAtom } from "@/store/authAtom";
import { chatSetWhisperTargetAtom } from "@/store/chatAtom";
import { useAutoAnimate } from "@formkit/auto-animate/react";
import { useAtomValue, useSetAtom } from "jotai";
import { useState } from "react";

const ChatBanner = () => {
  const {
    data: { roomId, users, notice },
    inviteUser,
  } = useChat();
  const [parentRef] = useAutoAnimate();
  const { id } = useAtomValue(authAtom);
  const setWhisperTarget = useSetAtom(chatSetWhisperTargetAtom);
  const [tooltip, setTooltip] = useState<Record<string, string>>({});

  const getUserInfo = async (userId: string) => {
    if (tooltip[userId]) return;

    const data = await requestUserInfo(userId);

    setTooltip((prev) => ({
      ...prev,
      [userId]: `${data.email} /
        Last Login: ${new Date(data.updated_at).toLocaleString()}`,
    }));
  };

  const onClickUserBadge = (targetUsername: string, targetUserId: string) => {
    // TODO: 개발 끝나면 풀기
    // if (targetUserId === id) return alert("You can't whisper to yourself");

    setWhisperTarget(targetUsername);
  };

  const onClickInvite = () => {
    const userTo = prompt("Type usename to Invite");

    if (!userTo) return;

    inviteUser({
      userFrom: id,
      userTo,
    });
  };

  const onClickWhisper = () => {
    const userTo = prompt("Type usename to Whisper");

    if (!userTo) return;

    setWhisperTarget(userTo);
  };

  return (
    <div className="text-center sticky top-0 z-10 space-y-2">
      <div className="mockup-browser border border-base-300 bg-base-100">
        <div className="mockup-browser-toolbar">
          <div className="bg-base-200 rounded-md flex-1 p-1">
            RoomID: {roomId}
          </div>
        </div>
      </div>

      {notice ? <div className="alert">[Notice] {notice}</div> : null}
      <ul
        className="flex flex-wrap justify-center items-center gap-2"
        ref={parentRef}
      >
        {users.map(({ user_id, user_name }, index) => (
          <li
            key={`${user_id}-${user_name}(${index})`}
            className="tooltip tooltip-bottom"
            data-tip={tooltip[user_id]}
          >
            <span
              className="badge badge-lg cursor-pointer"
              onMouseOver={() => getUserInfo(user_id.toString())}
              onClick={() => onClickUserBadge(user_name, user_id.toString())}
            >
              {user_name || "Unknown"}
            </span>
          </li>
        ))}

        <li>
          <button
            className="btn btn-xs btn-primary btn-outline bg-base-100"
            onClick={onClickInvite}
          >
            + Invite
          </button>
        </li>
        <li>
          <button
            className="btn btn-xs btn-primary btn-outline bg-base-100"
            onClick={onClickWhisper}
          >
            &gt;&gt; Whisper
          </button>
        </li>
      </ul>
    </div>
  );
};

export default ChatBanner;
