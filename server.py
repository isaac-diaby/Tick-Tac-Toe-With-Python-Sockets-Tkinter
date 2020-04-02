#!/usr/bin/env python3.7
# Isaac Diaby 090492276
# This is the server of the project. it will be used to talk to the database and execute SQL
from server_sql_connection import SqlServerConnection

import socket  # used to run the socket server
import select  # used to manage cuncurent connections to the server socket
import pickle  # parser that is used when accept and send any python class
# used to create multiple threads (in my case allow many players to play)
import _thread
import uuid    # used to generate a random ID using uuid()
import hashlib  # used to encrypt the password in the database


class SocketServer(socket.socket):
    def __init__(self):
        super().__init__(socket.AF_INET, socket.SOCK_STREAM)
        """
        - socket.AF_INET is saying our socket host's IP is going to be a IPv4 (Internet Protocol version 4)
        - socket.SOCK_STREAM is saying that the port that the socket will be using is a TCP (Transmission Control Protocol)
        """
        # gets the current host, internal network. replace with ("", PORT) for external network
        socketHostData = (socket.gethostname(), 4201)
        # binds the socket server to the current host name and listens to active connections
        self.bind(socketHostData)
        print(
            f"server started on Host: {socketHostData[0]} , Port: {socketHostData[1]}")

        # set max connection to 6
        self.listen(6)
        self.sockets_list = [self]

        # this SET will keep track of which client/s what is waiting to join a game
        self.waiting_queue = set()
        # this will keep track of all on going games
        self.onGoingGames = {}
        # this will store all connected users
        self.clients = {}

        # define the size of the length of the header
        self.HEADERSIZE = 10
        # connect to the database
        self.DB = SqlServerConnection()


        # Actions that authenticated users can call
        self.actions = {
            "[JOIN GAME]": self.joinGame,
            "[CANCEL GAME]": self.cancelGame,
            "[TAKE TURN]": self.takeTurn,
            "[GET ALL PLAYER STATS]": self.getAllPlayerStats
        }

        self._action_handler()

    def _action_handler(self):
        while True:
            # defines our read, write and errored listed sockets
            read_sockets, _write, error_sockets = select.select(
                self.sockets_list, [], self.sockets_list)

            for user_socket in read_sockets:
                if user_socket == self:
                    """
                    These will be the client sockets trying to connect to the server socket.
                    So in this block i will be authenticating client sockets.
                    """
                    # accept connections from server, this is so i can read the package
                    client_socket, client_address = self.accept()
                    print( client_socket, client_address)

                    # handle the incomming document action
                    client_action_document = self.recv_doc_manager(
                        client_socket)

                    if client_action_document is False:
                        # disconnection, left the sockect
                        continue

                    # HANDLE UNAUTHENTICATED USERS
                    if client_action_document["action"] == '[USER LOGIN]':  # Login attempt 
                        """
                        authenticate the user, this should return the user data in the database
                        if the username and password is correct. 
                        """
                        user = self.login_manager(
                            client_action_document["data"]) # get user data from database

                        if user["result"] is False:
                            # client failed to authenticate
                            # user[data] is the error message
                            client_socket.send(self.pkg_doc_manager(
                                "[USER LOGIN - FAIL]", user["data"]))
                            continue

                        # login user successful
                        # user[data] is the users account data
                        client_socket.send(self.pkg_doc_manager(
                            "[USER LOGIN - SUCCESS]", user["data"]))
                        self.sockets_list.append(client_socket) # Accept future request from this socket.
                        self.clients[client_socket] = user["data"] # keep track of who is logged in. 
                        print(
                            f'Accepted new connection from {client_address[0]}:{client_address[1]}, \
                            action_type: {client_action_document["action"]}, Username: {user["data"][0]}')
                        continue

                    if client_action_document["action"] == '[USER REGISTER]':  # Register attempt
                        # register the user in the db
                        create_account_status = self.registration_manager(
                            client_action_document["data"])

                        if create_account_status["result"] is False:
                            # something went wrong whilst creating the user account on the database
                            client_socket.send(self.pkg_doc_manager(
                                "[USER REGISTER - FAIL]", create_account_status["msg"]))
                            continue

                        # tell the client that they have successfully created an account tn the database
                        client_socket.send(self.pkg_doc_manager(
                            "[USER REGISTER - SUCCESS]", create_account_status["msg"]))
                        print('Created new account from {}:{}, action_type: {}'.format(
                            *client_address, client_action_document["action"]))
                        continue

                else:
                    """
                    At this point the connected client socket has already been authenticated
                    """
                    client_action_document = self.recv_doc_manager(
                        user_socket)
                    if client_action_document is False:
                        # disconnection, left the sockect
                        print(f'Closed connection from User:{self.clients[user_socket][0]}')
                        self.sockets_list.remove(user_socket)
                        del self.clients[user_socket]
                        continue

                    # handle any other action being passed to the server
                    print(f"{client_action_document['action']}: UserName: {self.clients[user_socket][0]}")
                    action = self.actions[client_action_document["action"]]
                    if action is False:
                        # this happends when the action type sent to the server isnt known
                        user_socket.send(self.pkg_doc_manager(
                            "[ERROR - ACTION]", f"Unregistered action type {client_action_document['action']}"))
                        continue

                    # start a new thread so that the action that is being sent doesn't hault reading other client messages
                    _thread.start_new_thread(
                        action, (user_socket, client_action_document["data"]))
                    continue

    def recv_doc_manager(self, client_socket):
        try:
            # Get the header of the package.
            message_header = client_socket.recv(self.HEADERSIZE)

            # This occures if the user disconnects or sends back no data.
            if not len(message_header):
                return False
            # Remove the extra spaces that we added in the HEADERSIZE and cast the tring into a integer.
            document_length = int(message_header.decode('utf-8').strip())
            # Get and store the actual action document that was sent to the server.
            doc = client_socket.recv(document_length)
            return pickle.loads(doc) # Turn bytes into a python object.

        except:
            return False

   
    def pkg_doc_manager(self, action, document):
        """
        Format the document that the server wants to send to the client socket to bytes.
        This will be done by pickling the doc object and adding the heading (length of
        the object in bytes).

        action  = The action type that is being packaged up.
        document = The data attached to the action.
        """
        # check if the action and its data are not left empty.
        if not action:
            raise('You can not send an empty action type')
        if not document:
            raise('You can not send an empty document')
        doc = {"action": action, "data": document}

        # This turns the python class into bytes that can be sent to the server.
        pkged_doc = pickle.dumps(doc)
        
        # The header will contain the length of the pkged_doc in bytes.
        pkged_doc_with_header = bytes(
            f"{len(pkged_doc):<{self.HEADERSIZE}}", 'utf-8')+pkged_doc
       
        return pkged_doc_with_header # this can be sent over the socket.

    def registration_manager(self, userCredentials):
        """
        Register the username on the database only if the username isnt taken

        userCredentials = ("username", "password")
        """
        try:
            c = self.DB.connection.cursor()
            c.execute("SELECT username FROM users WHERE username = :username", {
                "username": userCredentials[0]})
            userCredentials_fromDB = c.fetchone()
            # checks if there already a player with that username 

            if userCredentials_fromDB == None:
                # create new user WITH USERNAME AND PASSWORD because there is no user with the desired username
                hashedPassword = hashlib.md5() # set hashing algorithm to MD5 <not suitable for production>
                hashedPassword.update(bytes(userCredentials[1], 'utf-8')) # hash the provided password
               
                c.execute(
                    "INSERT INTO  users (username, password) VALUES (?, ?)", (userCredentials[0],  hashedPassword.hexdigest()))
                self.DB.connection.commit() 
                return {"result": True, "msg": "Account was created successfully."}
            else:
                return {"result": False, "msg": "Username already exists."}
        except BaseException as e:
            print(e)
            return {"result": False, "msg": "Error when creating client's account."}

    def login_manager(self, userCredentials:  ("username", "password") ):
        """
        Handle the authentication of the client.
        This function will query the database for the desired username and compare hashed passwords
        if they match, this will return the desired userdata <minus the hashed password>
        """
        try:
            c = self.DB.connection.cursor()
            c.execute("SELECT username, password FROM users WHERE username = :username", {
                "username": userCredentials[0]})
            userCredentials_fromDB = c.fetchone()
            

            if userCredentials_fromDB == None:
                # there is no accounts with the passed in username, return error
                return {"result": False, "data": f"No user found with the username: {(userCredentials[0])}"}
            
            hashedPassword = hashlib.md5() # set hashing algorithm to MD5 <not suitable for production>
            hashedPassword.update(bytes(userCredentials[1], 'utf-8')) # hash the provided password 
            # check if hashed passwords match
            if userCredentials_fromDB == (userCredentials[0], hashedPassword.hexdigest()): 
                c.execute("SELECT username, wins, loses, games_played FROM users WHERE username = ?",
                          (userCredentials[0],))
                userData = c.fetchone()
                
                return {"result": True, "data": userData} # return user data
            else:
                return {"result": False, "data": "Incorrect password"} # return error

        except BaseException as e:
            print(e)
            return {"result": False, "data": "Error when authenticating client's account."}

    def joinGame(self, client, data):
        """
        Adds the client to the waiting_queue
         if the client is the first one in the queue they will become host
          - the host will create the game session
        else they will get told to join a game by the server from the host request

        <difficulty>  the server can't send the socket class
        """
        try:
            # add user to game queue - session
            self.waiting_queue.add(client)
            host = False
            while (len(self.waiting_queue) < 2):  # this client is the only player in the game queue
                host = True  # this make setting up the game easier as one client will be responsible for setting it up
                if client in self.waiting_queue:  # if the client is still waiting in the for a game lobby
                    client.send(self.pkg_doc_manager(
                        "[JOIN GAME - WAITING]", data))
                else:
                    # "Client left the queue"
                    return

            if host:
                gameID = uuid.uuid1()
                Game_Board_Data = {
                    'id': gameID,
                    'player_data': [],
                    'board': [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
                    'player_turn': 1,
                }
                players = []
                for i in range(2):  # 2 player game
                    player_clinet = self.waiting_queue.pop()
                    players.append(player_clinet)
                    # let the clinet know that they are getting connected to a game.
                    # the socket client and their userData
                    Game_Board_Data['player_data'].append(
                        self.clients[player_clinet])
                for i, client in enumerate(players):
                    client.send(self.pkg_doc_manager(
                        "[JOIN GAME - SUCCESS]", Game_Board_Data))
                Game_Board_Data['clients'] = players

                # add the Game_Board_Data to the ongoing games data record
                self.onGoingGames[gameID] = Game_Board_Data
            return
        except:
            self.waiting_queue.remove(client)
            return

    def cancelGame(self, client, data):
        """
        remove client from waiting queue
        """
        if client in self.waiting_queue:
            self.waiting_queue.remove(client)
            client.send(self.pkg_doc_manager(
                        "[CANCEL GAME - SUCCESS]", "Cancelled"))
        else:
            client.send(self.pkg_doc_manager(
                        "[CANCEL GAME - FAIL]", "Not waiting for a game"))
        return

    def takeTurn(self, client, data):
        """
        - the clinet will pass the game id that they want to updata
        - then the server will send both clients the updated board

        <difficulty>  the server can't send the socket class so i have to create a clone of the data that the client sent
        """
        try:

            # update game board 
            self.onGoingGames[data["id"]]["board"] = data["board"]
            """
            Update player turn
            example: 
                player 1 starts:
                1 % 2 = 1, +1 = 2 turn
                2 % 2 = 0, + 1 = 1 turn 
            """
            data["player_turn"] = (data["player_turn"] % 2) + 1
            self.onGoingGames[data["id"]]["player_turn"] = data["player_turn"] 

            # check if any players won
            isWinner = self.check_if_winner(
                self.onGoingGames[data["id"]]["board"])

            if isWinner != 0:
                # notifiy players that the game has a winner
                data["winner"] = isWinner
                # go through all players in the current game
                for i, client in enumerate(self.onGoingGames[data["id"]]["clients"]):
                    # update database
                    if i+1 == data["winner"]:
                        # this client won the game
                        self.update_user_data_after_game(client, True)
                    else:
                        # this client lost or drew
                        self.update_user_data_after_game(client)
                    data["updated_userData"] = self.clients[client]
                    client.send(self.pkg_doc_manager("[GAME - END]", data))


                # close game session
                del self.onGoingGames[data["id"]]
                return

            for client in self.onGoingGames[data["id"]]["clients"]:
                client.send(self.pkg_doc_manager(
                            "[GAME - TURN]", data))
            return

        except:
            # close game session
            del self.onGoingGames[data["id"]]
            raise

    def check_if_winner(self, board: "Array: board state") -> int:
        """
        checks if there is a winning state
        """
        def allCheck(linearArray):
            """
            this function checks if the first element is the same as the rest of the array
            """
            return linearArray.count(linearArray[0]) == len(linearArray) and linearArray[0] != 0
        columns = [[], [], []]  # used to check if a player won Vertically
        zero_count = 0  # used to determine if the game board is a draw
        for row in board:
            # this will check each horizontal row
            if allCheck(row):
                return row[0]
            for columnIndex, col in enumerate(row):
                # split each col into a new array
                columns[columnIndex].append(col)
                
                if col == 0:
                    zero_count += 1
        for col in columns:
             # this will check each Vertical row
            if allCheck(col):
                return col[0]

        # check top-right to bottom left
        if len(set([board[i][i] for i in range(len(board))])) == 1:
            return board[0][0]
        # check top-left to bottom right
        if len(set([board[i][len(board)-i-1] for i in range(len(board))])) == 1:
            return board[0][len(board)-1]

        if zero_count == 0:
            # there is no more position to play/ the game is in a draw state
            return 3

        return 0  # no end state (the game is still playable - ongoing)

    def update_user_data_after_game(self, client, won=False):
        """
        update the players data on the server and the database after a game 
        """
        try:
            c = self.DB.connection.cursor()
            if won:
                c.execute("UPDATE users SET wins = wins+1, games_played=games_played+1 WHERE username = :username", {
                    "username": self.clients[client][0]})
                self.DB.connection.commit()
                print(self.clients[client][0], "won")
            else:
                c.execute("UPDATE users SET loses=loses+1, games_played=games_played+1 WHERE username = :username", {
                    "username": self.clients[client][0]})
                self.DB.connection.commit()
                print(self.clients[client][0], "lost")

            c.execute("SELECT username, wins, loses, games_played FROM users WHERE username = ?",
                      (self.clients[client][0],))
            userCredentials_fromDB = c.fetchone()
           

            # update client's data on the server
            self.clients[client] = userCredentials_fromDB
        except:
            raise
    def getAllPlayerStats(self, client, data):
        """
        Query the database for all users statistics and return them in an array
        """
        try:

            c = self.DB.connection.cursor()
            c.execute("SELECT username, wins, loses, games_played FROM users")
            userStatistics_fromDB = c.fetchall()
            
            client.send(self.pkg_doc_manager(
                            "[GET ALL PLAYER STATS - SUCCESS]", userStatistics_fromDB))
        except:
            client.send(self.pkg_doc_manager(
                            "[GET ALL PLAYER STATS - FAIL]", "Error whilst getting all player statistics"))

        



if __name__ == "__main__":  # only run this code if this python file is the root file execution
    server = SocketServer()
