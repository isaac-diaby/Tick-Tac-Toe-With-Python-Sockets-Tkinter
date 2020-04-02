#!/usr/bin/env python3.7
# Isaac Diaby 090492276
# This is the client of the project. It will be used to talk to the server.

import socket  # used to create the client socket connection with the server socket.
import pickle  # parser that is used to accept and send any python class.


# set up the socket


class ClientServerSocket(socket.socket):
    # default the host will be "socket.gethostname()" which in the current computer.
    # socketHostData will have to be passed if the server isnt running on the current computer.
    def __init__(self, socketHostData=(socket.gethostname(), 4201)):
        super().__init__(socket.AF_INET, socket.SOCK_STREAM)
        """"
        - socket.AF_INET is saying our socket host's IP is going to be a IPv4 (Internet Protical version 4)
        - socket.SOCK_STREAM is saying that the port that the socket will be using is a TCP (Transmission Control Protocol)
        """
        try:
            self.connect(socketHostData)
        except BaseException as e:
            print(e)
            raise ConnectionError(f"Could not connect to the HostName: {socketHostData[0]}, Port: {socketHostData[1]} - It may not exist or be down.")

        # define the size of the length of the header needs to be the same on the server
        self.HEADERSIZE = 10

        # is the user successfully authenticated?
        self.isAuth = False
        self.userData = None
        self.gameData = None
        # is client waitig to join a game?
        self.isWaiting = False
        # is client currently in a game?
        self.isInGame = False
        # Leaderboard 
        self.leaderboard = None
    

        # if self.isAuth is False:
        #    raise(BaseException("Password Or Username Was Incorrect"))

    async def recv_doc_manager(self):
        try:
            # get the header size
            message_header = self.recv(self.HEADERSIZE)

            # this occures if the user disconnects or sends back no data
            if not len(message_header):
                return False
            # this line will remove the extra spaces that we added in the HEADERSIZE and cast the tring into a integer
            document_length = int(message_header.decode('utf-8').strip())
            # this will store the actual document that was sent to the server
            doc = self.recv(document_length)

            return pickle.loads(doc)

        except BlockingIOError:
            return
        except:
            return False


    def pkg_doc_manager(self, action, document):
        """
        Handle the the document that the user wants to send to the socket server
        This will be done by pickling the doc object and adding the heading (length of
        the object in bytes)

        action  = The action type that is being packaged up.
        document = The data attached to the action
        """
        if not action:
            raise(BaseException("You can't send an empty action type"))
        if not document:
            raise(BaseException("You can't send an empty document"))
        doc = {"action": action, "data": document}
        # this turns the python class into bytes that can be sent to the server
        pkged_doc = pickle.dumps(doc)
        # The header will contain the length of the pkged_document bytes
        pkged_doc_with_header = bytes(
            f"{len(pkged_doc):<{self.HEADERSIZE}}", 'utf-8') + pkged_doc
        return pkged_doc_with_header

    #
    # This will get passed in a username and passwor -> the socket server will validate the user's Credential
    # Returns the user data if its valid, else it will return null
    #

    async def login(self, userCredentials):
        """
        Attempt to authenitcate the client with a username and password on the socket client 
        """
        # checks if the client isn't already authenticated
        if self.isAuth is False:
            packaged_auth_login_document = self.pkg_doc_manager(
                "[USER LOGIN]", userCredentials)
            self.send(packaged_auth_login_document)
            results = await self.recv_doc_manager()

            # nothing was sent back, something broke on the server (disconnected)
            if results is None:
                return False
            print(results["action"])
            if results["action"] == "[USER LOGIN - FAIL]":
                # user failed to authenticate client
                return results["data"]
            # successfully authenticated client's account
            self.userData = results["data"]
            self.isAuth = True
            return True

    async def register(self, userCredentials):
        '''
        Register the user on the socket server
        '''
        # checks if the client isn't already authenticated
        if self.isAuth is False:
            packaged_auth_register_document = self.pkg_doc_manager(
                "[USER REGISTER]", userCredentials)
            self.send(packaged_auth_register_document)
            results = await self.recv_doc_manager()
            
            # nothing was sent back, something broke on the server (disconnected)
            if results is None:
                return "Error: no connection to the socket"

            if results["action"] == "[USER REGISTER - FAIL]":
                # failded to create user account client
                return results["data"]

            # successfully created user account
            return results["data"]

    async def joinGame(self):
        # checks if the client is already authenticated
        if self.isAuth is True and self.isWaiting is False and self.isInGame is False:
            packaged_join_game_request_document =  self.pkg_doc_manager(
                "[JOIN GAME]", self.userData[0])
            self.send(packaged_join_game_request_document)
            self.isWaiting = True

            results = await self.recv_doc_manager()

            if results is None:  # nothing was sent back, something broke on the server (disconnected)
                self.isWaiting = False 
                return "Error: no connection to the socket"

            while results["action"] == "[JOIN GAME - WAITING]":
                results = await self.recv_doc_manager()
                if results is None:
                    self.isWaiting = False 
                    return "Error: no connection to the socket"

            if  results["action"] == "[CANCEL GAME - FAIL]":
                # no in the waiting game queue
                return results["data"]

            self.isWaiting = False 
            # if  results["action"] == "[JOIN GAME - CANCELLED]":
            #     # cancelled game
            #     return results["data"]

                # the client is connecting 
            if  results["action"] == "[JOIN GAME - SUCCESS]":
                # successfully joined a game
                self.isInGame = True
                self.gameData = results["data"]
                return True
        
            if  results["action"] == "[CANCEL GAME - SUCCESS]":
                # cancelled game
                self.isWaiting = False
                return results["data"]
            


    async def cancelGame(self):
        """
        leave the game queue
        """
        # checks if the client is already authenticated
        if self.isAuth is True and self.isWaiting is True and self.isInGame is False:
            packaged_leave_game_queue_document =  self.pkg_doc_manager(
                "[CANCEL GAME]", self.userData[0])
            self.send(packaged_leave_game_queue_document)

    async def startGameLoop(self, frame):
        """
        listens to any updates from the server 
        """
        try: 
            results = await self.recv_doc_manager()

            if results is None:  # nothing was sent back, something broke on the server (disconnected)
                self.isWaiting = False 
                return "Error: no connection to the socket"

            while results["action"] == "[GAME - TURN]":
                self.gameData = results["data"]
                frame.render()
                results = await self.recv_doc_manager()
                if results is None:
                    self.isInGame = False
                    return "Error: no connection to the socket"
            
            if  results["action"] == "[GAME - END]":
                self.gameData = results["data"]
                self.userData = self.gameData["updated_userData"]
                # game ended
                if self.gameData["winner"] == 3: 
                    frame.MSG.set("Draw!")
                else:
                    frame.MSG.set("Player "+ str(self.gameData["winner"])+" has won!")
                frame.render()
                frame.msg_label.grid()
                frame.end_game_btn.grid()
                self.isInGame = False
                return 

        except:
            self.isInGame = False
            self.gameData = None
            raise


    async def take_turn(self, rowCol):
        """
        make an action on the board by sending the data to the socket server
        """
        # make sure the player is in a game
        if self.isAuth is True and self.isInGame is True:

            # update board
            self.gameData["board"][rowCol[0]][rowCol[1]] = self.gameData["player_turn"]

            # send the take turn action to the server
            packaged_game_board_action_document =  self.pkg_doc_manager(
                "[TAKE TURN]", self.gameData)
            self.send(packaged_game_board_action_document)
        return

    
    async def getAllPlayerData(self):
        # make sure the client is authenticated and not in a game
        try:
           if self.isAuth is True and self.isInGame is False:
            packaged_get_player_all_data_action_document =  self.pkg_doc_manager(
                "[GET ALL PLAYER STATS]", self.userData[0])
            self.send(packaged_get_player_all_data_action_document)
            results = await self.recv_doc_manager()
            
            # nothing was sent back, something broke on the server (disconnected)
            if results is None:
                return "Error: no connection to the socket"

            if results["action"] == "[GET ALL PLAYER STATS - FAIL]":
                # failded to get user statistics 
                self.leaderboard = None
                return results["data"]

            # successfully get user statistics 
            self.leaderboard = self.insertion_sort(results["data"]) # sort the player data 
            return True
        except:
            raise   


    def insertion_sort(self, userStats):
            """
            Sort each player by number of games won  (Descending order)
            """
            # TODO: implement insertion sort here
            for userIndex in range(1, len(userStats)): # go through the whole array so each user has been sorted.
                # i dont have to so minus 1 cause in range(starting point, endpoint but not including >)
                current_user = userStats[userIndex]
                position = userIndex
                while (position > 0) and (userStats[position-1][1] < current_user[1]):
                    # checks if the lower user index is lower and the index number is checking both index 1 and 0
                    userStats[position] = userStats[position-1]
                    position -= 1
                
                # place the current userdata in its highest possition 
                userStats[position] = current_user
            
            # userStats is now sorted - with the players with the highest numbers of wins last. 
            return userStats     
        

if __name__ == "__main__":  # only run this code if this python file is the root file execution
    try:
        s = ClientServerSocket()
        s.login(("test", "tEst3_14159"))
        
    except ConnectionError as e:
        print(e)
        
