#!/usr/bin/env python3.7
# Isaac Diaby 090492276

# the client views and page routing
import tkinter as tk  # Ui builder
from tkinter import ttk # leaderboard UI builder

"""
lets the program run async-ly (controls whether or not to wait 
for a process to finish before moving on to the next or leave it 
to run in the back ground)
"""
import asyncio

# the client socket controller that is used by the ui/client, this will have all the actions that the client can perform.
from client_socket_connection import ClientServerSocket

# used to create multiple threads (in my case allow the client to wait to join a game and be able to cancel without needing the 'join a game' function to return a value and end)
import _thread


class Application(tk.Tk):
    # can pass in anything as an array
    def __init__(self, *args):
        super().__init__(*args)  # inits the inherited Tk class

        # adds some meta data to the application
        self.title("Tic Tac Toa Project")
        # locked the app min dimensions
        self.minsize(700, 600)
        # self.maxsize(700, 600) # i can add a max dimension here
        '''
         self is the tk.TK root instance
         creates the first frame an passes the root TK instance to it. This means that all the function that are generated in the Application class will be accessable to the container frame

         - A frame is like a view for tkinter, im going to be rebuilding frames and bringing it to the front of the application window to simulate navigation.
        '''
        container = tk.Frame(self)
        self.PreviousFrame =  None

        # use full width and height and fill it. define the columbs and rows
        container.pack(side="top", fill="both", expand=True, anchor='center')
        container.grid_rowconfigure(0, weight=1)
        container.grid_rowconfigure(1, weight=1)
        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)

        # set the socket server connection variable to None, with will be initialize the ClientServerSocket class once the user successfully authenticates
        self.SocketConnection: ClientServerSocket = None

        # self.frames will contain all the different views of the application. ie login, lobby and game views.
        self.frames = {}
        # go through all the tk.frames and render them, one on top the other
        for FView in (HomePage, JoinGamePage, GamePage, LeaderBoardPage, AuthenticationPage):
            # makes a referance to the frame class and feeds it the required information. container is the the passed down TK and the single view that will get updated every time i want to switch views
            frame = FView(container, self)
            # saves the instance in self.frames
            self.frames[FView] = frame
            # adds the initial widget rendered.
            # frame.grid(row=0, sticky="news")
        # Goes to the login page
        self.PreviousFrame = self.frames[AuthenticationPage]
        self.switch_frame_to(AuthenticationPage)

    def switch_frame_to(self, frame: tk.Frame):
        """
        This function allows navigation between frame (views).
        """
        # tries to find the frame instance in self.frames
        frame = self.frames[frame]
        if frame != None:  # check if there is an initialize frame that has been created.
            self.PreviousFrame.grid_remove() # remove the last frame so the page will resize to best fit heigh and width
            frame.grid(row=0, sticky="news")
            self.PreviousFrame = frame
            # then re-build the frame but with the new frame.
            frame.render()  # each frame view should have this method, it allows me to re-render views with updated Data
            frame.tkraise()  # brings the fram to the front of the window.
        return

    def authenticate_user(self, Frame: tk.Frame, userCredentials: "(username: String, Passowrd: String)", socketHostData: "(HostName: String, Port: Number)"):
        """
        This procedure will attempt to connect to the server socket by passing the address and port to ClientServerSocket.
        Then try to authenticate the client by passing user credentials in the login function in the ClientServerSocket class.
        If the user credentials are correct then the client will be authenticated and navigated to the home page.
        Else the user won't be authenticated and will be told what is wrong.
        """
        try:
            if ((len(userCredentials[0]) > 0) and (len(userCredentials[1]) > 5)):
                print("Attempt to authenticate client", userCredentials[0])
                # initialize the ClientServerSocket class and point to the socket server with its address and port
                self.SocketConnection = ClientServerSocket(socketHostData)
                # attempt to authenticate the client and wait for the login function to return.
                result = asyncio.run(
                    self.SocketConnection.login(userCredentials))
                if self.SocketConnection.isAuth == True:
                    print("Clinet authenticated: True")
                    # Switch to the home page
                    Frame.err_label.grid_remove()
                    self.switch_frame_to(HomePage)                    
                    return
                else:
                    print("Clinet authenticated: Fail")
                    # Display any additional information
                    Frame.ERROR_MSG.set(result)
                    Frame.err_label.grid()
            else:
                # display error message
                Frame.ERROR_MSG.set("Password must be 6 characters or more" if (len(
                    userCredentials[0]) > 0) else "Username must be 1 character or more")
                Frame.err_label.grid()
        except ConnectionError as e:
            print(e)
            Frame.ERROR_MSG.set("Can't Reach the Server Socket")
            Frame.err_label.grid()

    def register_user(self, Frame: tk.Frame, userCredentials: "(username: String, Passowrd: String)", socketHostData: "(HostName: String, Port: Number)"):
        """
        This procedure will attempt to connect to the server socket by passing the address and port to ClientServerSocket.
        Then try to create a new user account by passing a unique username and a password to the register function in the ClientServerSocket class.
        If the username is unique the server will create the user account, the user will have to login after this to authenticate the client.
        Else the user's account won't be created in the database and will be told what is wrong.
        """
        try:
            if ((len(userCredentials[0]) > 0) and (len(userCredentials[1]) > 5)):
                print("Attempt to create new user account", userCredentials[0])
                # initialize the ClientServerSocket class and point to the socket server with its address and port
                self.SocketConnection = ClientServerSocket(socketHostData)
                result = asyncio.run(
                    self.SocketConnection.register(userCredentials))  # attempt to create a new user account in the database and wait for the register function to return.
                # Display any additional information
                Frame.ERROR_MSG.set(result)
                Frame.err_label.grid()
            else:
                # display error message
                Frame.ERROR_MSG.set("Password must be 6 characters or more") if (len(
                    userCredentials[0]) > 0) else Frame.ERROR_MSG.set("Username must be 1 character or more")
                Frame.err_label.grid()

        except ConnectionError as e:
            print(e)
            Frame.ERROR_MSG.set("Can't Reach the Server Socket")
            Frame.err_label.grid()


class HomePage(tk.Frame):  # inherit from the tk frame
    """
    The main page - shown when the user is successfully authenticated
    - The client will bew presented with the home page rendered view which will include the following:
      - The currently logged in user's account statistics.
      - "Join game" button that will tell the server that this client wants to join a game and to add it in the waitling list queue
      - "View leader board" button that will switch the view to the Leader Board Page.

      + at the bottom of the view there is a section for displaying any error, the message is the value of self.ERROR_MSG
    """

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)  # inits the inherited frame class
        # parent is the class that called this class
        # print(self.__dict__) # shows me the attributes of this variable
        self.controller = controller
        self.parent = parent
        self.ERROR_MSG = tk.StringVar()
        self.render()

    def render(self):
        """
        Render the home page view
        """
        if self.controller.SocketConnection != None:
            # "Welcome: " + username
            # - Wins: {self.controller.SocketConnection.userData[1]} - Loses: {self.controller.SocketConnection.userData[2]} - Total games played: {self.controller.SocketConnection.userData[3]}
            tk.Label(self, text=f"Welcome: {self.controller.SocketConnection.userData[0]}", font=(
                "arial", 15, "bold")).grid(row=0, column=0, ipadx=20, pady=10,  padx=60, sticky="news")
        tk.Button(self, text='Join A Game', font=("arial", 20, "bold"), command=lambda:  self.join_game(
        )).grid(row=1,  padx=130, ipadx=80, ipady=20, pady=10, sticky="news")
        tk.Button(self, text='Leader-board', font=("arial", 20, "bold"), command=lambda: self.controller.switch_frame_to(LeaderBoardPage)).grid(row=2,
                                                                                                                                                padx=130, ipadx=80, ipady=20, pady=90, sticky="news")
        self.err_label = tk.Label(
            self, textvariable=self.ERROR_MSG, font=("arial", 20, "bold"))
        self.err_label.grid(row=3, rowspan=2, ipadx=10, sticky="ews")

    def join_game(self):
        """
        join game lobby queue,
            if successful-> enter game session.
            else -> go back to the home page if the player decides to quit the queue.
        """
        print("Join game queue")
        self.controller.switch_frame_to(JoinGamePage)
        # this allows the player to canccel at any time whilst waiting for someone else to join the game.
        _thread.start_new_thread(self.waiting_to_Join, ())

    def waiting_to_Join(self):
        try:
            res = asyncio.run(self.controller.SocketConnection.joinGame())
        except AttributeError:  # this will throw an error if the client is trying to get into a game without being authentecated by the server
            # send the client to the login page
            self.controller.switch_frame_to(AuthenticationPage)
            raise UserWarning("Currently not signed in")
        if self.controller.SocketConnection.isInGame is True:
            self.controller.switch_frame_to(GamePage)
            # start game loop
            asyncio.run(
                self.controller.SocketConnection.startGameLoop(self.controller.frames[GamePage]))
            self.ERROR_MSG.set("")
        else:
            self.controller.switch_frame_to(HomePage)
            self.ERROR_MSG.set(res)
        return


class JoinGamePage(tk.Frame):  # inherit from the tk frame
    """
    The Join game page - shown when the client attempts to join a game session and is waiting for a player to join the game.
    - The client will bew presented with the rendered view which will include the following:
        - A message of whats happening ("Waiting For Another Player To Join...")
        - A butten to leave the queue and to go back to the home view
    """

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)  # inits the inherited frame class
        # parent is the class that called this class
        # print(self.__dict__) # shows me the attributes of this variable
        self.controller = controller
        self.parent = parent

        self.render()

    def render(self):
        tk.Label(self, text="Waiting For Another Player To Join...", font=("", 22,)).grid(
            row=0, column=0, columnspan=3, padx=80, ipadx=30, ipady=90, sticky="news")
        tk.Button(self, text="Cancel", font=("arial", 20, "bold"), command=self.cancel_game).grid(
            row=1, column=1, pady=20, ipadx=80, ipady=20, sticky="ews")

    def cancel_game(self):
        """
        Leave the game waiting queue and navigate back to the home page
        """
        try:
            asyncio.run(self.controller.SocketConnection.cancelGame())
        except AttributeError:  # this will throw an error if the user manages to get un authenticated by the server and tries to leave game the queue
            # send the client to the login page
            self.controller.switch_frame_to(AuthenticationPage)
            raise UserWarning("Currently not signed in")


class GamePage(tk.Frame):  # inherit from the tk frame
    """
    The main page - shown when the user is successfully authenticated
    """

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)  # inits the inherited frame class
        # parent is the class that called this class
        # print(self.__dict__) # shows me the attributes of this variable
        self.controller = controller
        self.parent = parent

        self.MSG = tk.StringVar()

        # render view
        self.render()

    def render(self):
        # game board section
        if self.controller.SocketConnection != None:
            gameBoard_section = tk.Frame(self)
            self.renderBoard(gameBoard_section)
            gameBoard_section.grid(sticky="news", row=0,
                                   column=0, padx=130, pady=20)
            tk.Label(self, text=f"Player 1: {self.controller.SocketConnection.gameData['player_data'][0][0]}", font=(
                "arial", 14)).grid(row=1, sticky="nsw",  padx=130)
            tk.Label(self, text=f"Player 2: {self.controller.SocketConnection.gameData['player_data'][1][0]}", font=(
                "arial", 14)).grid(row=2, sticky="nsw",  padx=130)
            tk.Label(self, text=f"Turn: Player {self.controller.SocketConnection.gameData['player_turn']}", font=(
                "arial", 14)).grid(row=3, sticky="nsw",  padx=130)

            # Setup  Message Label
            end_of_gmae_section = tk.Frame(self)

            self.end_game_btn = tk.Button(end_of_gmae_section, text="Go Back to home", font=(
                "arial", 14), command=lambda: self.controller.switch_frame_to(HomePage))
            self.end_game_btn.grid(
                row=0, column=1, ipadx=30, ipady=20, padx=10, pady=10)
            self.end_game_btn.grid_remove()
            self.msg_label = tk.Label(
                end_of_gmae_section, textvariable=self.MSG, font=("arial", 14))
            self.msg_label.grid(row=0, sticky="news")
            self.msg_label.grid_remove()
            end_of_gmae_section.grid(row=4, sticky="news")

    def renderBoard(self, boardSection):
        """
        - from the board array it will output the game board in a frame.
         <difficulty>  Tkinter doesnt like buttons being generated in a for loop, (all buttons will have the same command as the last button generated)
         ie in a 3 x 3 board you will always select possition (2,2) AKA the last box. 
        """
        for row in range(len(self.controller.SocketConnection.gameData["board"])):
            for column in range(len(self.controller.SocketConnection.gameData["board"][row])):
                slotState = self.controller.SocketConnection.gameData["board"][row][column]
                if slotState == 2:
                    tk.Button(boardSection, bg="#0000FF", state="disabled").grid(
                        row=row, column=column, ipadx=50, ipady=40, padx=10, pady=10)
                elif slotState == 1:
                    tk.Button(boardSection, bg="#FF0000", state="disabled").grid(
                        row=row, column=column, ipadx=50, ipady=40, padx=10, pady=10)
                else:
                    # <difficulty> so i have to explicitly tell the lambda function that i want to use the variables in passed at the time of the button was created
                    tk.Button(boardSection, command=lambda row=row, col=column: self.take_turn(row, col)).grid(
                        row=row, column=column, ipadx=60, ipady=40, padx=10, pady=10)

    def take_turn(self, row, Column):
        rowColumn = (row, Column)
        try:
            if (self.controller.SocketConnection.userData[0] == self.controller.SocketConnection.gameData["player_data"][self.controller.SocketConnection.gameData["player_turn"]-1][0]):
                asyncio.run(
                    self.controller.SocketConnection.take_turn(rowColumn))
                self.msg_label.grid_remove()
        except:
            self.MSG.set("It is not your turn")
            self.msg_label.grid()
            pass


class LeaderBoardPage(tk.Frame):  # inherit from the tk frame
    """
    The leaderBoard page - shows the top players, and lets the user search up any players rank (including thier own)
    """

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)  # inits the inherited frame class
        # parent is the class that called this class
        # print(self.__dict__) # shows me the attributes of this variable
        self.controller = controller
        self.parent = parent

        # variables
        self.MSG = tk.StringVar()
        self.MSG.set("Your Rank Is:")
        self.userDatas = []

        # render view
        self.render()

    def render(self):
        if self.controller.SocketConnection != None:
            # username will be used to lookup a single user's ranking
            username = tk.StringVar()
            username.set(self.controller.SocketConnection.userData[0])

            asyncio.run(self.get_all_userData_sorted())
            Leaderboard = ttk.Treeview(self, columns=('username', 'wins', 'losses', 'games_played'))
            Leaderboard.column('#0', width=60, anchor='center')
            Leaderboard.heading('#0', text='Ranking')
            Leaderboard.column('username', width=120, anchor='center')
            Leaderboard.heading('username', text='Username')
            Leaderboard.column('wins', width=60, anchor='center')
            Leaderboard.heading('wins', text='Wins')
            Leaderboard.column('losses', width=60, anchor='center')
            Leaderboard.heading('losses', text='Losses')
            Leaderboard.column('games_played', width=120, anchor='center')
            Leaderboard.heading('games_played', text='Games Played')

            for index in range(0, (20 if (len(self.userDatas) > 19) else len(self.userDatas))):  # Display top 20 players!
                Leaderboard.insert("", tk.END, text=str(index+1), values=self.userDatas[index] )

            Leaderboard.grid(row=0,  padx=10, pady=20,
                              ipady=140, sticky="nw")

            # right hand side section
            right_action_section = tk.Frame(self)
            right_action_section.grid(
                row=0, rowspan=2, column=1, ipady=120, pady=20)

            tk.Button(right_action_section, text="Update Board", font=(
                "arial", 16), command=self.render).grid(row=0, columnspan=2, sticky="new", ipadx=10, ipady=10)

            # search player section
            search_player_section = tk.Frame(right_action_section)
            search_player_section.grid(
                row=1, rowspan=2, columnspan=2, padx=20, pady=70)

            tk.Label(
                search_player_section, text="Username:", font=("arial", 14)).grid(row=0, column=0, sticky="news")
            tk.Entry(
                search_player_section, textvariable=username).grid(row=0, column=1, pady=20, padx=10, ipady=10, ipadx=20, sticky="swe")

            tk.Button(search_player_section, text="Search \nPlayer Rank", font=(
                "arial", 16), command=lambda: self.findUserRank(username.get())).grid(row=1, column=0, sticky="new", padx=5, ipadx=20)
            tk.Button(search_player_section, text="Get My \nPosition", font=(
                "arial", 16), command=lambda: self.findUserRank(self.controller.SocketConnection.userData[0])).grid(row=1, column=1, sticky="new", padx=5, ipadx=20)

            tk.Button(search_player_section, text="Go Back to home", font=(
                "arial", 14), command=lambda: self.controller.switch_frame_to(HomePage)).grid(row=3, columnspan=2, column=0, pady=10, padx=20, ipadx=30, ipady=20)
            tk.Label(search_player_section, textvariable=self.MSG, wrap=255, font=(
                "arial", 14)).grid(row=4, columnspan=2, sticky="sw", pady=20)

    async def get_all_userData_sorted(self):
        """
        get all user datas from the database via the server connection
        """
        # get all user stats data from the server (username, wins, loses, games_played)
        # fetch_all_user_stats = [("isaac", 12,0,12), ("test1", 0,10,10), ("test2", 4,10,14), ("test3", 10,4,14)]
        try:
            self.MSG.set("")
            fetch_all_user_stats = await self.controller.SocketConnection.getAllPlayerData()
            if fetch_all_user_stats != True:
                self.MSG.set(fetch_all_user_stats)
            self.userDatas = self.controller.SocketConnection.leaderboard
        except:
            raise

    def findUserRank(self, username: str):
        for i, userdata in enumerate(self.userDatas):
            if userdata[0] == username:
                return self.MSG.set(f"Rank of {username}: {i+1} ")
            else:
                pass
        return self.MSG.set(f"Could not find {username}")


class AuthenticationPage(tk.Frame):  # inherit from the tk frame
    """
    The main page - shown when the user is successfully authenticated
    """

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)  # inits the inherited frame class
        # parent is the class that called this class
        # print(self.__dict__) # shows me the attributes of this variable
        self.controller = controller
        self.parent = parent
        self.ERROR_MSG = tk.StringVar()
        self.render()

    def render(self):
        """
        Render the authentication page view
        """
        # variables
        username = tk.StringVar()
        password = tk.StringVar()
        hostname = tk.StringVar()
        port_number = tk.IntVar()

        # testing login info:
        # username.set("test1")
        # password.set("test12")
 

        # set up default server connection value
        # server is running on the current computer
     
        # hostname.set("localhost") # server is running on the current computer
        port_number.set(4201) # on this port number

        # authentication section
        authentication_section = tk.LabelFrame(
            self, text="Authentication", font=("arial", 20, "bold"))

        username_label = tk.Label(
            authentication_section, text="Username:", font=("arial", 14))
        username_entry = tk.Entry(
            authentication_section, textvariable=username)
        password_label = tk.Label(
            authentication_section, text="Password:", font=("arial", 14))
        password_entry = tk.Entry(
            authentication_section,  show="*", textvariable=password)

        """
            placing Widgets:

            placement:
            - row = vertical placement  
            - column = horizontal placement
            alignment:
            - sticky = n="top", e="right", s="bottom", w="left" alignment
            padding:
            - padx =  the extra space around the x axis 
            - pady =  the extra space around the y axis 
            - ipadx =  the extra space inside the widget on the x axis 
            - ipady =  the extra space inside the widge on the y axis 
            """
        username_label.grid(row=0, column=0, sticky="nsw", ipadx=40, ipady=10)
        username_entry.grid(row=0, column=1, sticky="nsw",
                            ipadx=40, ipady=10, padx=10, pady=10)
        password_label.grid(row=1, column=0, sticky="nsw", ipadx=40, ipady=10)
        password_entry.grid(row=1, column=1, sticky="nsw",
                            ipadx=40, ipady=10, padx=10, pady=10)
        authentication_section.grid(
            row=0, sticky="news",  padx=130, ipadx=20, pady=20, ipady=10)

        # server info section
        server_info_section = tk.LabelFrame(
            self, text="Server Info", font=("arial", 20, "bold"))

        hostname_label = tk.Label(
            server_info_section, text="Host name:",  font=("arial", 15))
        hostname_entry = tk.Entry(server_info_section, textvariable=hostname)
        port_number_label = tk.Label(
            server_info_section, text="Port number:",  font=("arial", 15))
        port_number_entry = tk.Entry(
            server_info_section, textvariable=port_number)

        hostname_label.grid(row=0, column=0, sticky="nsw", ipadx=40, ipady=10)
        hostname_entry.grid(row=0, column=1, sticky="nsw",
                            ipadx=40, ipady=10, padx=10, pady=10)
        port_number_label.grid(
            row=1, column=0, sticky="nsw", ipadx=40, ipady=10)
        port_number_entry.grid(row=1, column=1, sticky="nsw",
                               ipadx=40, ipady=10, padx=10, pady=10)
        server_info_section.grid(row=1, sticky="news",
                                 padx=130, ipadx=20, pady=20, ipady=10)

        # action section
        action_section = tk.Frame(self)
        # make the action section share single column
        action_section.grid_columnconfigure(0, weight=1)
        action_section.grid_columnconfigure(1, weight=1)
        action_section.grid_rowconfigure(0, weight=1)
        action_section.grid_rowconfigure(1, weight=1)

        # Make sure that the fields are not empty
        loginBtn = tk.Button(action_section, text='Login', font=("arial", 20, "bold"), command=lambda: self.controller.authenticate_user(
            self, (username.get(), password.get()), (hostname.get(), port_number.get())))
        registerBtn = tk.Button(action_section, text='Register', font=("arial", 20, "bold"), command=lambda: self.controller.register_user(
            self, (username.get(), password.get()), (hostname.get(), port_number.get())))

        loginBtn.grid(row=0, column=0, sticky="news",
                      ipadx=5, pady=5, ipady=10, padx=10)
        registerBtn.grid(row=0, column=1, sticky="news",
                         ipadx=5, pady=5, ipady=10,  padx=10)
        action_section.grid(row=2, sticky="news",  padx=130,
                            ipadx=20, pady=20, ipady=10)

        # Setup Error Message Label
        self.err_label = tk.Label(self, textvariable=self.ERROR_MSG)
        self.err_label.grid(row=3, sticky="news")
        self.err_label.grid_remove()


if __name__ == "__main__":  # only run this code if this python file is the root file execution
    try:
        # starts the application
        app = Application()
        app.mainloop()
    except:
        # catches for any unauthenticated.
        #  print("Unable to get Authenticated user")
        pass
