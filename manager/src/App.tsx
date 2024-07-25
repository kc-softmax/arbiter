import React, { useState } from "react";
import "./App.css";

const App: React.FC = () => {
  const [leftTopList, setLeftTopList] = useState<string[]>([
    "Item 1",
    "Item 2",
  ]);
  const [leftBottomList, setLeftBottomList] = useState<string[]>([
    "Item 3",
    "Item 4",
  ]);
  const [rightList, setRightList] = useState<string[]>(["Item 5", "Item 6"]);

  const addItem = (
    listSetter: React.Dispatch<React.SetStateAction<string[]>>
  ) => {
    listSetter((prevList) => [...prevList, `Item ${prevList.length + 1}`]);
  };

  const removeItem = (
    listSetter: React.Dispatch<React.SetStateAction<string[]>>
  ) => {
    listSetter((prevList) => prevList.slice(0, -1));
  };

  return (
    <div className="container">
      <div className="left-pane">
        <div className="left-top">
          <h3>Left Top List</h3>
          <ul>
            {leftTopList.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
          <button onClick={() => addItem(setLeftTopList)}>Add</button>
          <button onClick={() => removeItem(setLeftTopList)}>Remove</button>
        </div>
        <div className="left-bottom">
          <h3>Left Bottom List</h3>
          <ul>
            {leftBottomList.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
          <button onClick={() => addItem(setLeftBottomList)}>Add</button>
          <button onClick={() => removeItem(setLeftBottomList)}>Remove</button>
        </div>
      </div>
      <div className="right-pane">
        <h3>Right List</h3>
        <ul>
          {rightList.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
        <button onClick={() => addItem(setRightList)}>Add</button>
        <button onClick={() => removeItem(setRightList)}>Remove</button>
      </div>
    </div>
  );
};

export default App;
