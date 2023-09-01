"use client";

import { LikeOrDislike } from "@/@types/chat";
import { ChatActionType, ChatActions } from "@/const/actions";
import { chatAtom } from "@/store/chatAtom";
import { useAtomValue } from "jotai";
import { useCallback } from "react";

export const useChat = () => {
  const {
    error,
    eventMessage,
    messages,
    notice,
    roomId,
    users,
    ws,
    lobbyRoomList,
    inviteMessage,
  } = useAtomValue(chatAtom);

  const sendSocketBase = useCallback(
    <T extends object>(action: ChatActionType, data: T) => {
      const chatData: {
        action: ChatActionType;
        data: T;
      } = {
        action,
        data,
      };

      ws?.send(JSON.stringify(chatData));
    },
    [ws]
  );

  const sendMessage = (message: string) => {
    sendSocketBase(ChatActions.MESSAGE, {
      room_id: roomId,
      message,
    });
  };

  const createRoom = (nextRoomId: string, maxUsers: number = 50) => {
    if (roomId === nextRoomId) return;

    sendSocketBase(ChatActions.ROOM_CREATE, {
      room_id: nextRoomId,
      max_users: maxUsers,
    });
  };

  const changeRoom = (nextRoomId: string) => {
    if (roomId === nextRoomId) return;

    sendSocketBase(ChatActions.ROOM_CHANGE, {
      room_id_from: roomId,
      room_id_to: nextRoomId,
    });
  };

  const joinRoom = (nextRoomId: string) => {
    if (roomId === nextRoomId) return;

    sendSocketBase(ChatActions.ROOM_JOIN, {
      room_id: nextRoomId,
    });
  };

  const sendNotice = (message: string) => {
    sendSocketBase(ChatActions.NOTICE, {
      room_id: roomId,
      message,
    });
  };

  const sendWhisper = ({
    message,
    userId,
    whisperTarget,
  }: {
    message: string;
    userId: string;
    whisperTarget: string;
  }) => {
    console.log(
      "userId, message, whisperTarget :>> ",
      userId,
      message,
      whisperTarget
    );
    // sendSocketBase(ChatActions.WHISPER, {
    //   message,
    //   user_id: userId,
    //   whisper_target: whisperTarget,
    // });
  };

  const refreshLobby = useCallback(() => {
    sendSocketBase(ChatActions.LOBBY_REFRESH, {});
  }, [sendSocketBase]);

  const inviteUser = ({
    userFrom,
    userTo,
  }: {
    userFrom: string;
    userTo: string;
  }) => {
    sendSocketBase(ChatActions.USER_INVITE, {
      room_id: roomId,
      user_id_from: parseInt(userFrom, 10),
      user_name_to: userTo,
    });
  };

  const sendLike = (messageId: number, type: LikeOrDislike) => {
    sendSocketBase(ChatActions.MESSAGE_LIKE, {
      room_id: roomId,
      message_id: messageId,
      type,
    });
  };

  return {
    data: {
      roomId,
      notice,
      messages,
      users,
      lobbyRoomList,
    },
    inviteMessage,
    error,
    eventMessage,
    sendMessage,
    createRoom,
    changeRoom,
    joinRoom,
    sendNotice,
    sendWhisper,
    refreshLobby,
    inviteUser,
    sendLike,
  };
};
