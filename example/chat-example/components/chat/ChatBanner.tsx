"use client";

import { authAtom } from "@/store/authAtom";
import { useAtomValue } from "jotai";
import { useState } from "react";

export interface ChatBannerProps {
  roomId: string;
  users: string[];
}

const ChatBanner = ({ roomId, users }: ChatBannerProps) => {
  const { token } = useAtomValue(authAtom);
  const [tooltip, setTooltip] = useState<Record<string, string>>({});

  const requestUserInfo = async (user: string) => {
    if (tooltip[user]) return;

    // TODO: 유저 정보 요청으로 바꿀 예정
    const response = await fetch(
      "http://192.168.0.48:8880/auth/console/console-user",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          authorization: `Bearer ${token}`,
        },
        // TODO: 진짜 유저 id로 바꿀 예정
        body: JSON.stringify({ id: 1 }),
      }
    );

    const result = await response.json();

    setTooltip((prev) => ({
      ...prev,
      [user]: `${result.email}
        Last Login: ${result.updated_at}`,
    }));
  };

  return (
    <div className="text-center sticky top-0 z-10">
      <p className="font-semibold">RoomID: {roomId}</p>
      <div>
        {users.map((user, index) => (
          <p
            key={user + index}
            className="tooltip tooltip-bottom"
            data-tip={tooltip[user]}
          >
            <span className="badge" onMouseOver={() => requestUserInfo(user)}>
              {user}
            </span>
          </p>
        ))}
      </div>
    </div>
  );
};

export default ChatBanner;
