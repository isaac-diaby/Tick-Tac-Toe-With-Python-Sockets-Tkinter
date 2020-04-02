# Tic Tac Toe With Socket Project

This is a Tic-tac-toe game written in python version 3.7.4 and powered by a python sockets. The application is separated into two different sections: client.py and server.py. 

#### Main Files
> client.py: This file manages everything that the client sees and interact with to communicate to the socket server.
> server.py: All clients must interact with the socket server which is created in this file. The file manages all the game board and the queue match making logic, credential validations + encryption, authentication and client to client interactions.

#### Secondary Files
> client_socket_connection.py: This file contains all the actions that the client can send to the socket server. its responsible for storing and minipulate the data that is recieved from the server to the client.



## Getting started
Your will need to have python3.7 already installed [here](https://www.python.org/).

Next, i've made some batch scripts for window used to easily get started with 2 click, if your using any other Operating system (OS) you will have to just run the commands the terminal (this should be the same)

Start the server by running the "Run the server" batch file.
```
py server.py
```
> You should take note of the computer hostname/ip, the default port should be port 4201 (you can change this value in the server code), 
 __In the case of an error make sure that the port is open and available !__

After, start the client window by running the "Run the client" batch file.
```
py client.py
```
> You should set the values of the hostname and port to point to the socket server (that you noted in the step above)  
__In the case of an error make sure that socket server is up and running and that you are correctly pointing to the socket server!__







