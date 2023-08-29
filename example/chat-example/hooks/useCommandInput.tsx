import { useState } from "react";

interface UseCommandInputParams {
  [command: string]: (data: string) => void;
}

export const useCommandInput = (commands: UseCommandInputParams) => {
  const [messageInput, setMessageInput] = useState("");
  const [command, setCommand] = useState<string | null>(null);

  const resetMessageInput = () => {
    setMessageInput("");
  };

  const resetCommand = () => {
    setCommand(null);
  };

  const onChangeMessageText = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessageInput(e.target.value);

    Object.keys(commands).forEach((command) => {
      const commandRegex = new RegExp(`^${command}\\s+`);
      const commandMatch = e.target.value.match(commandRegex);

      if (commandMatch) {
        setCommand(command);
        setMessageInput("");

        return;
      }
    });
  };

  const onSubmitWithCommand = (
    e?: React.FormEvent<HTMLFormElement>,
    callback?: () => void
  ) => {
    e?.preventDefault();

    if (messageInput.trim() === "") {
      return;
    }

    if (command) {
      commands[command](messageInput);
      resetCommand();
      resetMessageInput();
      return;
    }

    callback?.();
    resetMessageInput();
  };

  return {
    command,
    controls: {
      message: {
        value: messageInput,
        onChange: onChangeMessageText,
      },
      form: {
        onSubmit: onSubmitWithCommand,
      },
    },
    reset: resetMessageInput,
    resetCommand,
  };
};
