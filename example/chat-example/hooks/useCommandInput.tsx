import { useState } from "react";

interface UseCommandInputParams {
  [command: string]: {
    name: string;
    action: (data: string) => void;
  };
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
      commands[command].action(messageInput);
      resetCommand();
      resetMessageInput();
      return;
    }

    callback?.();
    resetMessageInput();
  };

  const CommandAutoComplete = () => {
    const onClickCommandAutoComplete = (command: string) => {
      setCommand(command);
      setMessageInput("");
    };

    return (
      <div className="dropdown dropdown-open dropdown-top">
        <ul
          tabIndex={0}
          className="dropdown-content z-[1] menu p-2 shadow rounded-box space-y-2"
        >
          {Object.keys(commands)
            .filter(
              (commandKey) =>
                messageInput.length && commandKey.indexOf(messageInput) === 0
            )
            .map((commandKey) => (
              <li key={commandKey}>
                <button
                  className="btn btn-sm btn-block btn-outline"
                  type="button"
                  onClick={() =>
                    onClickCommandAutoComplete(commands[commandKey].name)
                  }
                >
                  {commandKey} : {commands[commandKey].name}
                </button>
              </li>
            ))}
        </ul>
      </div>
    );
  };

  return {
    commands,
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
    components: {
      CommandAutoComplete,
    },
  };
};
