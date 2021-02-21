```
   __________  ____  __    ___    __  _______  __  ________  __
  / ____/ __ \/ __ \/ /   /   |  /  |/  / __ )/ / / / __ \ \/ /
 / /   / / / / / / / /   / /| | / /|_/ / __  / / / / /_/ /\  / 
/ /___/ /_/ / /_/ / /___/ ___ |/ /  / / /_/ / /_/ / _, _/ / /  
\____/\____/\____/_____/_/  |_/_/  /_/_____/\____/_/ |_| /_/   
                                                               
```

# Table of Contents

- [Coolambury](#coolambury)
  * [Game Flow](#game-flow)
  * [Authors and Responsibilities:](#authors-and-responsibilities-)
  * [Main Packages Used:](#main-packages-used-)
  * [Setup](#setup)
    + [Running the Server](#running-the-server)
    + [Running the Client](#running-the-client)
    + [Config File](#config-file)
  * [Game GUI Showcase](#game-gui-showcase)
    + [Start Window](#start-window)
    + [Game Window](#game-window)
    + [Drawing HistoryWindow](#drawing-historywindow)
- [NN Model](#nn-model)

# Coolambury

*Coolambury* is a word guessing and drawing game - commonly known as *charades*. The game was created by a group of 4 Masters Degree students from the University of Technology and Science in Poland, Kraków (AGH). The goal of the project was to create an application using web communication between clients. In order to satisfy the requirements, we have chosen to create a Socket based Server alongside the Client written mainly in PyQt5.

## Game Flow
___
The client allows the user to specify his/her nickname used in the game as well as choose the desired game room from the list or using a game room code. Users can also create a room, therefore becoming a host. BOT joins every room by default. When a sufficient amount of players (2 + BOT) join the room, the game can be started by the game host. An artist is chosen by the game server and is presented with three word options to choose from and later draw it. Both the artist and the person who will have guessed are awarded points. As time passes users are given hints of the words (subsequent letters are being unveiled). The game finishes when any of the players gather 500 points.
## Authors and Responsibilities:
___

**Michał Loska - @michalloska**
  - Client Communication with Server (Sockets)
  - Partial PyQt5 implementation
  - PyTest
  - Pre-commit package configuration

**Michał Zbrożek - @Atloas**
  - Client Implementation in PyQt

**Adrian Wysocki - @theratty**
  - Server Implementation
  - Game Communication

**Piotr Witkoś - @Witkod**
  - QuickDraw Bot Implementation

## Main Packages Used:
___
- PyQt5
- PyTest
- QuickDraw
- Pre-commit

## Setup

### Running the Server
___
Server can be run using a simple command:

> make server

### Running the Client
___
Client can be run with a command:

> make client <_config_file_._json_>

or when using powershell with the following commands:

> env:PYTHONPATH = "./Client"

> python .\Client\RunClient.py .\configRemote.json
### Config File
___

Config file stores Connection setup data which allows the Client to connect to the game server

example config file:
```
{
    "PORT": 5050,
    "HEADER_LEN": 256,
    "SERVER": "localhost",
    "model_path": "./Server/resources/model.h5",
    "labels_path": "./Server/resources/labels.csv"
}
```
where *labels_path* is a list of existing game phrases and *model_path* is a pre-supplied bot model (should remain untouched)

## Game GUI Showcase

### Start Window
___
The *StartWindow* is the first window presented to the User. Here we specify our nickname and choose the desired game room by double clicking on the list or passing the game room code and pressing Join Room button <br>
![StartWindow](.readme_img/StartWindow_NicknameNotValid.png)
![StartWindow](.readme_img/StartWindow.png)
### Game Window
___

The *GameWindow* is the game lobby window. The state presented below represents the moment when players can still join the room and the game has not started yet. Start button is only active for the host of the room. <br>
![StartWindow](.readme_img/GameWindow_NotStarted.png)<br>
Artist was chosen, now he/she needs to pick the word to be drawn.
![StartWindow](.readme_img/GameWindow_WordSelection.png)<br>
As the players draw and guess each player is awarded points and the scoreboard is located on the left-hand side of the window. On the right-hand side of the window, there is a chat where players place their guesses. BOT also sends its messages there. If nothing is being drawn it becomes annoyed and sends a rude message :)
![StartWindow](.readme_img/GameWindow_candle.png)<br>
The Bot can also guess the actual word! <br>
![StartWindow](.readme_img/GameWindow_BotGuessed.png)<br>

### Drawing HistoryWindow
___
Once the round is finished all players are presented with a window with a window containing previews of all the drawings in that round <br>
![StartWindow](.readme_img/DrawingHistoryWindow.png)<br>

# Bot NN Model

In our project neuron network model has a role of an additional player in every game who only tries to guess an answer. He can't draw but anyway "he" scores his points if he forestall other users.

We used a Convolutional Neuron Network architecture.
Network has been trained on subset of data which comes from quickdraw dataset which contains more than 50 milion drawings across 345 categories.
Data which is recognised are simplified drawings stored in Numpy bitmaps. Bitmaps are 28x28 grayscale images.

The model is created from folowing layers:
Conv2D(32, (5,5), activation='relu')
MaxPooling2D(pool_size=(2, 2))
Conv2D(128, (3, 3), activation='relu')
MaxPooling2D(pool_size=(2, 2))
Dropout(0.2)
Flatten()
Dense(512, activation='relu')
Dense(256, activation='relu')
Dense(num_classes, activation='softmax')

Every category has been trained on 5000 examples of drawings.

Here is the result of training process:
![alt text](https://github.com/jtheiner/SketchRecognition/blob/master/SketchRecognition/recognition/models/345/5000/training_process.png?raw=true)

The network accuracy shows following confusion matrix:
![alt text](https://github.com/jtheiner/SketchRecognition/raw/master/SketchRecognition/recognition/models/20/10000/confusion_matrix.png)
