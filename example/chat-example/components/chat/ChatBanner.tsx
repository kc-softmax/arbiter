"use client";

import { requestUserInfo } from "@/api/auth";
import { useChat } from "@/hooks/useChat";
import { authAtom } from "@/store/authAtom";
import { useAtomValue } from "jotai";
import { useState } from "react";

const ChatBanner = () => {
  const {
    data: { roomId, users, notice },
    inviteUser,
  } = useChat();
  const { id } = useAtomValue(authAtom);
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

  const onClickInvite = () => {
    const userTo = prompt("Type usename to Invite");

    if (!userTo) return;

    inviteUser({
      userFrom: id,
      userTo,
    });
  };

  return (
    <div className="text-center sticky top-0 z-10 space-y-2">
      <div className="mockup-browser border border-base-300">
        <div className="mockup-browser-toolbar">
          <div className="bg-base-200 rounded-md flex-1 p-1">
            RoomID: {roomId}
          </div>
        </div>
      </div>

      {notice ? <div className="alert">[Notice] {notice}</div> : null}
      <ul className="flex flex-wrap justify-center items-center gap-2">
        {users.map(({ user_id, user_name }, index) => (
          <li
            key={`${user_id}-${user_name}(${index})`}
            className="tooltip tooltip-bottom"
            data-tip={tooltip[user_id]}
          >
            <span
              className="badge badge-lg"
              onMouseOver={() => getUserInfo(user_id.toString())}
            >
              {user_name || "Unknown"}
            </span>
          </li>
        ))}

        <li>
          <button
            className="btn btn-xs btn-primary btn-outline"
            onClick={onClickInvite}
          >
            + Invite
          </button>
        </li>
      </ul>
    </div>
  );
};

export default ChatBanner;
