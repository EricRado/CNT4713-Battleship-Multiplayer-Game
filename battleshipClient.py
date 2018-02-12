############################################################################
#                                                                          #
#                           BATTLESHIPS CLIENT                             #
#                                                                          #
#                          By: Francisco Lozada                            #
#                                Eric Rado                                 #
#                                                                          #
############################################################################

from tkinter import *
import tkinter.scrolledtext as tkst
from socket import *
from threading import *
import os
import copy
import sys
import pickle
import queue

#CHAT global variables
hostname = 'localhost'
ftpPort = 13000
udpPort = 12000

#BATTLESHIP global variables
BUFFER_SIZE = 5052
all_players = {}
tlist = []
all_boards = {}
ships = {
        "Aircraft Carrier":5,
        "Battleship":4,
        "Submarine":3,
        "Destroyer":3,
        "Patrol Boat":2
        }

class ChatWindow:
    def __init__(self,tcp,udp,addr):
        #user information variables
        self.username = ''
        self.udp = udp
        self.udpServAddr = addr
        self.myAddr = ()
        self.team = ''
        self.tcp = tcp
        self.online = False

        #if user is online disables the login button from trying to login again
        self.loginDisable = False
        self.startDisable = False
        #used to start one receive msg thread
        self.receiveCounterThread = 0

        self.start()


    def start(self):
        global tlist

        print('Starting client GUI...')

        self.initDisplay()

        self.startUpMsg()

        #change the title of the window
        self.root.wm_title('BATTLESHIP CHAT GUI : ')

        self.root.mainloop()

        print('Stopping client GUI...')

    def initDisplay(self):
        self.root = Tk()
        self.root.resizable('1','1')
        self.root.configure(bg = 'gray')

        #setup frames for borders
        self.gameFrame = Frame(self.root,bd = 4)
        self.gameFrame.pack(side = TOP, fill =Y)

        self.displayFrame = Frame(self.root,bd=2)
        self.displayFrame.pack(side = TOP, fill =Y)

        self.inputFrame = Frame(self.root,bd = 2)
        self.inputFrame.pack(side = TOP, fill = Y)


        self.top = Frame(self.gameFrame, bd=4, relief=SUNKEN)
        self.middle = Frame(self.displayFrame, bd=4, relief=SUNKEN)
        self.bottom = Frame(self.inputFrame, bd=2, relief=SUNKEN)


        #pack the frames
        self.top.pack(fill=Y)
        self.middle.pack(fill=Y)
        self.bottom.pack(fill=Y)


        #setup text messages display and a send message entry
        self.displayGame = tkst.ScrolledText(self.top,width = 75,height = 30)
        self.displayGame.configure(background = 'black',fg = 'green')
        self.displayMsg = tkst.ScrolledText(self.middle,
                width = 75, height= 15)

        self.inputMsg = Text(self.bottom,
                width = 50,height = 2,)


        #setup buttons
        self.sendButton = Button(self.root,text = "SEND",bg = 'gray',
                    command = self.sendMessage)
        self.quitButton = Button(self.root,text = "QUIT",bg = 'gray',
                    command = self.logout)
        self.loginButton = Button(self.root,text = "LOGIN",bg = 'gray',
                    command = self.login)
        self.startButton = Button(self.root,text = "START",bg = 'gray',
                    command = self.startThread)

        #Compute display position of all objects
        self.displayGame.pack(side = TOP, fill = BOTH)
        self.displayMsg.pack(side = TOP, fill = BOTH)
        self.inputMsg.pack(side = LEFT, fill = BOTH)

        self.sendButton.pack(side = LEFT)
        self.loginButton.pack(side = LEFT)
        self.startButton.pack(side = LEFT)
        self.quitButton.pack(side = LEFT)

    def help(self):
        self.displayMsg.insert(END,'QUIT       --> Quit chat server.\n')
        self.displayMsg.insert(END,'SEND       --> Send a message.\n')
        self.displayMsg.insert(END,'@ -color --> Send a message to all team members '
                                    'of specified color.\n')
        self.displayMsg.insert(END,'             If no color is specified default '
                                'will be current team color.\n')
        self.displayMsg.insert(END,'list     --> Print out list of all current'
                                ' online users.\n')
        self.displayMsg.insert(END,'#help     --> Print help message.\n')

##########################################################################
##                           RECEIVE MSG THREAD                         ##
##########################################################################
    def receiveMsgs(self):
        print('started receiver...')
        while(True):
            message,addr = self.udp.recvfrom(4096)
            if(message.decode() == 'quit'):
                self.displayMsg.insert(END,'GUI terminating...\n')
                break
            decodeMsg = message.decode()
            print(decodeMsg)
            self.displayMsg.insert(END,decodeMsg + '\n')

    #SEND messages
    def sendMessage(self):
        #store message input by the user
        cmd = self.inputMsg.get("0.0",END+"-1c")
        self.inputMsg.delete('0.0',END)
        modMessage = self.username + ' : ' + cmd
        myMsg = 'YOU : '+cmd
        #prints out help display
        if(cmd.upper() == '#HELP'):
            self.displayMsg.insert(END,cmd + '\n')
            self.help()
        else:
            self.displayMsg.insert(END,myMsg +'\n')

            self.udp.sendto(modMessage.encode(),self.udpServAddr)

    #logout using quit button
    def logout(self):
        if(self.online):
            msg = self.username + ' : !Q'
            self.udp.sendto(msg.encode(),self.udpServAddr)
        else:
            self.tcp.send('quit'.encode())
            self.killThread = True

        self.root.quit()

    #get username and color inputs from text input
    def getCredentials(self):
        #type username and team color
        response = self.inputMsg.get("0.0",END+"-1c")
        self.inputMsg.delete('0.0',END)
        self.tcp.send(response.encode())

        #store username and team color into class variables
        tokens = response.split()
        self.username = tokens[0]
        self.team = tokens[1]

        #verify if user is team red or blue
        if(self.team.upper() == 'RED' or self.team.upper() == 'BLUE'):
            #set user online
            self.online = True
            self.root.wm_title('BATTLESHIP GUI : '+ self.username)
            self.sendUdpAddr()

    #send udp address to server
    def sendUdpAddr(self):
        connMsg = self.username + ' : ' +' CONNECTIONTEST'
        self.udp.sendto(connMsg.encode(),self.udpServAddr)

        #send upd address to server with secure tcp socket
        self.myAddr = self.udp.getsockname()
        sendAddr = str(self.myAddr)
        self.tcp.send(sendAddr.encode())
        self.loginDisable = True
        self.receiveCounterThread = self.receiveCounterThread +  1


    #start a receive msg thread and player thread
    def startThread(self):
        global tlist

        if(not self.startDisable):
            #Disable start button because you only start game once
            self.startDisable = True
            #Start a thread to receive messages
            self.send  = Thread(target = self.receiveMsgs, args =())
            self.send.start()
            tlist.append(self.send)

            #Start a thread to start Battleship game
            self.playerThread = ClientThread(self.username,self.team,self.tcp,
                        self.displayGame,self.bottom,self.root)
            self.playerThread.start()
            tlist.append(self.playerThread)

        else:
            self.displayMsg.insert(END,'Game and Chat has already launched.\n')

    #send server username and team color
    def login(self):
        #does not run other functions if user is already logged in
        if(self.loginDisable):
            self.displayMsg.insert(END,'Already logged in.\n')
            return None

        #grabs user input and verifies team color
        if(not self.online):
           self.getCredentials()

        #receive logged in confirmation or error message
        message = self.tcp.recv(1024).decode()
        self.displayMsg.insert(END,message + '\n')
        if(self.online):
            self.displayMsg.insert(END,'Press START to launch Battleship Game.\n')


    #initial message sent by server
    def startUpMsg(self):
        message = self.tcp.recv(1024).decode()
        self.displayMsg.insert(END,message + '\n')


##########################################################################
##                           PLAYER THREAD                              ##
##########################################################################


class ClientThread(Thread):

    global all_boards, all_players, ships,username,team

    #CHECKED
    def __init__(self,username,team,client_socket,displayGame,bottom,root):

        Thread.__init__(self)

        #user local variables
        self.username = username
        self.team = team
        self.client_socket = client_socket
        self.board = None
        self.gameDisplay = displayGame
        self.bottom = bottom

        #used to control while loop for setting ships positions
        self.x = 0
        self.y = 0
        self.orientation = ''
        self.validOrien = False
        self.validCoords = False

        #used to control while loop for playing game
        self.validCmd = False
        self.quitIsInput = False

        #used to disable buttons if set to True
        self.orientationDisable = True
        self.coordinatesDisable = True
        self.battleshipDisable = True

        #setup BATTLESHIP TEXT INPUT
        self.inputGameMsg = Text(self.bottom,width = 20,height = 2,fg ='green')
        self.inputGameMsg.configure(background = 'black')
        self.inputGameMsg.configure(insertbackground = 'green')
        self.inputGameMsg.pack(side = RIGHT,fill =BOTH)

        #setup BATTLESHIP BUTTONS
        self.battleShipButton = Button(root,text = "Attack",bg = 'gray',
                    command = self.attackPlayer)
        self.battleShipButton.pack(side = RIGHT)
        self.coordinateButton = Button(root,text = "Set Coordinates",bg = 'gray',
                    command = self.get_coor)
        self.coordinateButton.pack(side = RIGHT)
        self.orientationButton = Button(root,text = "Set Orientation",bg = 'gray',
                    command = self.v_or_h)
        self.orientationButton.pack(side = RIGHT)


    #WORK
    def attackPlayer(self):
        # BATTLESHIPS GAME PLAY LOGIC
        check = True

        #Get user attack command input
        cmd = self.inputGameMsg.get("0.0",END+"-1c")
        self.inputGameMsg.delete('0.0',END)
        tokens = cmd.split()

        #Player enters quit to end game
        if (cmd.upper() == 'QUIT'):
            self.gameDisplay.insert(END,"Goodbye!\n")
            self.client_socket.send('quit'.encode())
            self.validCmd = True
            self.quitIsInput = True
            return None

        #Test for a valid command input
        if(len(tokens) != 3):
            self.gameDisplay.insert(END,"Insufficient amount of inputs.\n")
            self.gameDisplay.insert(END,'Input example : [targetname] [x coor] [y coor]\n')
            return None

        target_player = tokens[0]
        y = int(tokens[1])-1
        x = int(tokens[2]) -1

        modMsg = target_player + ' ' + str(y) + ' ' + str(x)

        #Check if coodinates are betwen 1 to 10
        if (x > 9 or x < 0 or y > 9 or y < 0):
            self.gameDisplay.insert(END,"Invalid entry. Please use values between 1 to 10 only.\n")
            return None
        check = self.checkIfTargetIsValid(target_player)

        if(check):
            # Send Attack command to server
            self.client_socket.send(modMsg.encode())
        else:
            return None

        #Response from the server based on the attack cmd previously sent
        result = self.client_socket.recv(BUFFER_SIZE).decode()
        self.gameDisplay.insert(END,result + '\n')

        if (result == 'WIN'):
            self.gameDisplay.insert(END,"You Won!\n")
            self.validCmd = True
            return None

        self.gameDisplay.insert(END,"Your turn is over.\n")

        #Break input lock while loop
        self.validCmd = True


    ############################
    ##          SETUP         ##
    ############################

    #Sets a board for a player
    def setup_board(self):
        # Create blank_board
        self.board = []
        for i in range(10):
            board_row = []
            for j in range(10):
                board_row.append(-1)
            self.board.append(board_row)


        # Add ships as last element in the array
        self.board.append(copy.deepcopy(ships))
        # Placing ships on the board

    #Runs loop to put each of the five different ships on the board
    def place_ships(self):
        global ships

        self.gameDisplay.insert(END,'Please enter coordinates (row,col) then press'
                                    ' SET COORDINATES.\n')
        self.gameDisplay.insert(END,'Please enter orientation (v,h)for vertical '
                                        'or horizontal\nthen press SET ORIENTATION.\n')

        for ship in ships.keys():

            #get coordinates from user and validate the position
            valid = False
            while(not valid):
                self.print_board(self.username, self.board)
                self.gameDisplay.insert(END,"\nPlacing a/an " + ship+'\n')
                #set a lock to wait for coordinate and orientation user input
                self.setInputLock('board setup')
                valid = self.validate(ships[ship],self.x,self.y,self.orientation)
                if (not valid):
                    self.gameDisplay.insert(END,"Cannot place a ship there.\nPlease take a look at the board and try again.\n")

            #place the ship after validation
            self.place_ship(ships[ship],ship[0],self.orientation,self.x,self.y)

        self.print_board(self.username, self.board)
        self.gameDisplay.insert(END,"Done placing user ships. \n")


    ##################################
    ##          PRINT BOARD         ##
    ##################################

    def print_board(self, player, playerboard):

        if (player == self.username):

            # PRINT YOUR OWN BOARD

            self.gameDisplay.insert(END,"{:=^62}\n".format("| " + player.upper() + "'S BOARD |") )

            # print horizontal numbers
            self.gameDisplay.insert(END,' {}\n'.format(''.join(['   {}  '.format(i+1) for i in range(10)])) )
            for i in range(10):
                self.gameDisplay.insert(END,'\n{:<2d}  {}'.format(i+1, '  |  '.join([' ' if playerboard[i][j] == -1 else playerboard[i][j] for j in range(10)])))
                if i != 9:
                    self.gameDisplay.insert(END,'\n'+ '   ' + '-' * 58 )  # print a horizontal line
            self.gameDisplay.insert(END,'')
            self.gameDisplay.insert(END,"\n==============================================================\n")

        else:

            # PRINT OPPONENT BOARDS

            self.gameDisplay.insert(END,"{:=^62}\n".format("| " + player.upper() + "'S BOARD |") )

            # print horizontal numbers
            self.gameDisplay.insert(END,' {}\n'.format(''.join(['   {}  '.format(i+1) for i in range(10)])))

            for i in range(10):
                line = ''
                for j in range(10):
                    if ( playerboard[i][j] == '*' ):
                        line += '*'
                    elif ( playerboard[i][j] == '$' ):
                        line += '$'
                    else:
                        line += ' '
                    if j != 9:
                        line += '  |  '
                self.gameDisplay.insert(END,'\n{:<2d}  {}'.format(i+1, line) )

                if i != 9:
                    self.gameDisplay.insert(END,'\n'+'   ' + '-' * 58)  # print a horizontal line
            self.gameDisplay.insert(END,'')
            self.gameDisplay.insert(END,"\n==============================================================\n")


    def print_all_boards(self):
        global all_boards

        for player, board in all_boards.items():
            self.print_board(player, board)


    ##################################
    ##          GAME LOGIC          ##
    ##################################


    def update_game_info(self):
        global all_boards, all_players

        # Update player board statuses
        print("Updating all board statuses....")
        all_boards = pickle.loads(self.client_socket.recv(BUFFER_SIZE))
        print("Board statuses updated.")

        # Update active players list
        print("Updating active players list....")
        all_players = pickle.loads(self.client_socket.recv(BUFFER_SIZE))
        self.printListOfAllPlayers()
        print("All active player names received.")


    #Checks if target is a valid user or they are on the same team
    def checkIfTargetIsValid(self,target_player):
        global all_players

        # Validate target specified by user
        for key in all_players:
            if(key == target_player):
                if(all_players[key] == self.team):
                    self.gameDisplay.insert(END,'Sorry you have selected a player\n '
                    'from your own team, please try again\n')
                    self.printListOfAllPlayers()
                    return False
                else:
                    return True


        self.gameDisplay.insert(END,"Sorry the player you entered does not exist,"
                        " please try again\n")
        self.printListOfAllPlayers()
        return False

    #Get coordinates from user input, activated when coor button is pressed
    def get_coor(self):
        if(self.coordinatesDisable):
            return None
        user_input = self.inputGameMsg.get("0.0",END+"-1c")
        self.inputGameMsg.delete('0.0',END)

        try:
            #see that user entered 2 values seprated by comma
            coor = user_input.split(",")
            if (len(coor) != 2):
                self.gameDisplay.insert(END,"Invalid entry, too few/many coordinates.\n")
                self.gameDisplay.insert(END,'Please enter coordinates (row,col) then press'
                                ' SET COORDINATES.\n')

            else:
                #check that 2 values are integers
                coor[0] = int(coor[0])-1
                coor[1] = int(coor[1])-1

                #check that values of integers are between 1 and 10 for both coordinates
                if coor[0] > 9 or coor[0] < 0 or coor[1] > 9 or coor[1] < 0:
                    self.gameDisplay.insert(END,"Invalid entry. Please use values between 1 to 10 only.\n")
                    self.gameDisplay.insert(END,'Please enter coordinates (row,col), then press '
                                'SET COORDINATES.\n')
                else:
                    #if everything is ok, return coordinates
                    self.gameDisplay.insert(END,'Valid coordinates entry.\n')
                    self.x = coor[0]
                    self.y = coor[1]
                    self.validCoords = True

        except ValueError:
            self.gameDisplay.insert(END,"Invalid entry. Please enter only numeric values for coordinates.\n" )
        except Exception as e:
            self.gameDisplay.insert(END,str(e)+'\n')

    #Get orientation from user input, activated when orientation button is pressed
    def v_or_h(self):
        if(self.orientationDisable):
            return None
        user_input = self.inputGameMsg.get("0.0",END+"-1c").lower()
        self.inputGameMsg.delete('0.0',END)

        if ((user_input.lower() == "v") or (user_input.lower() == "h")):
            self.orientation = user_input
            self.validOrien = True
            self.gameDisplay.insert(END,"Valid orientation entry.\n")
        else:
            self.gameDisplay.insert(END,"Invalid entry. Please only enter v or h.\n")
            self.gameDisplay.insert(END,"vertical or horizontal (v,h) ?, then press SET"
                                    "ORIENTATION \n")

    #Validate coordinates and orientation before placing it on the board
    def validate(self, ship, x, y, ori):
        check = True
        #validate the ship can be placed at given coordinates
        if ori == "v" and x+ship > 10:
            check = False
        elif ori == "h" and y+ship > 10:
            check = False
        else:
            if ori == "v":
                for i in range(ship):
                    if self.board[x+i][y] != -1:
                        check = False

            elif ori == "h":
                for i in range(ship):
                    if self.board[x][y+i] != -1:
                        check = False
        if(not check):
            #reset thread variables for next iteration
            self.x = 0
            self.y = 0
            self.orientation = ''
            self.validOrien = False
            self.validCoords = False

        return check

    #After validation is successful place the ship on the board
    def place_ship(self, ship, s, ori, x, y):

        #place ship based on orientation
        if ori == "v":
            for i in range(ship):
                self.board[x+i][y] = s
        elif ori == "h":
            for i in range(ship):
                self.board[x][y+i] = s

        #reset thread variables for next iteration
        self.x = 0
        self.y = 0
        self.orientation = ''
        self.validOrien = False
        self.validCoords = False

    #function checks if user input a valid orientation and coordinate entry
    #or a valid attack cmd is inserted
    def setInputLock(self,msg):
        if(msg == 'board setup'):
            while(True):
                if (self.validOrien and self.validCoords) :
                    break
        if(msg == 'attack setup'):
            while(True):
                if(self.validCmd):
                    break

    #print list of all online players with their corresponding team color
    def printListOfAllPlayers(self):
        global all_players
        self.gameDisplay.insert(END,"           LIST OF PLAYERS \n")
        self.gameDisplay.insert(END,'=========================================\n')

        for user in all_players:
            color = all_players[user]
            msg = user + '     ' + color
            self.gameDisplay.insert(END,msg + '\n')
        self.gameDisplay.insert(END,'\n')

    #Sets a wait for different portions of the code such as waiting for
    #certain amount of players to connect to server, waiting for all players
    #to setup their boards and waiting for your turn.
    def waitForPlayers(self,cmd):
        #recieve a wait msg or ready msg
        msg = self.client_socket.recv(4096).decode()

        if(msg == 'Waiting for more players to connect...'):
            self.gameDisplay.insert(END,msg + '\n')
            self.client_socket.recv(4096).decode()
        elif(msg == 'Waiting for all players to set their boards...'):
            self.gameDisplay.insert(END,msg + '\n')
            self.client_socket.recv(4096).decode()
        elif(msg == 'Please wait for your turn...'):
            self.gameDisplay.insert(END,msg + '\n')
            endGameMsg = self.client_socket.recv(4096).decode()
            #If match is over msg recv break out of while loop
            #and display the team who won
            if(endGameMsg == 'MATCH IS OVER.'):
                self.gameDisplay.insert(END,'MATCH IS OVER.\n')
                msg2 = self.client_socket.recv(4096).decode()
                self.gameDisplay.insert(END,msg2 + '\n')
                self.quitIsInput = True
                return None

        if(cmd == 'conn'):
            self.gameDisplay.insert(END,'All players connected. \n')
        elif(cmd == 'setup'):
            self.gameDisplay.insert(END,'All players have setup their boards. \n')
        elif(cmd == 'wait'):
            self.gameDisplay.insert(END,'It is your turn.\n')

    def run(self):
        global all_players

        self.gameDisplay.insert(END,'BATTLESHIP intiated... \n')
        self.waitForPlayers('conn')

        #Enable board setup buttons
        self.orientationDisable = False
        self.coordinatesDisable = False
        self.battleshipDisable = False

        self.setup_board()

        #Placing ships on the board
        self.place_ships()

        #Sending board to game server
        print("Sending board...")
        self.client_socket.send(pickle.dumps(self.board))
        print("Board sent!")

        #Disable board setup buttons
        self.orientationDisable = True
        self.coordinatesDisable = True
        self.battleshipDisable = True


        #Wait for all players to set their boards up
        self.waitForPlayers('setup')

        #Ready for Gamer to play
        while(not self.quitIsInput):
            #Wait for player turn to play
            self.waitForPlayers('wait')

            if(not self.quitIsInput):
                #Print out other players board
                self.update_game_info()
                self.print_all_boards()
                self.gameDisplay.insert(END,'To attack, input target username folowed by'
                                ' the coordinates you\nwish to attack.\n\n')
                self.gameDisplay.insert(END,'Example Foo 3 5\n\n')
                self.gameDisplay.insert(END,"Remember:    * = miss    $ = hit\n\n")
                #Waits for user to input an attack or quit cmd
                self.setInputLock('attack setup')
            else:
                break

            #Reset input lock to False for next turn
            self.validCmd = False

        print('BATTLESHIP ENDED....')

def main():

    #setup a tcp socket
    tcpAddr = (hostname,ftpPort)
    tcp = socket(AF_INET,SOCK_STREAM)
    tcp.setsockopt(SOL_SOCKET,SO_REUSEADDR,1)
    tcp.connect(tcpAddr)

    #setup a udp socket
    udpAddr = (hostname,udpPort)
    udp = socket(AF_INET,SOCK_DGRAM)
    udp.setsockopt(SOL_SOCKET,SO_REUSEADDR,1)

    #start tkinier chat GUI
    window = ChatWindow(tcp,udp,udpAddr)
    for t in tlist:
        t.join()

#RUN MAIN
main()
