############################################################################
#                                                                          #
#                           BATTLESHIPS SERVER                             #
#                                                                          #
#                          By: Francisco Lozada                            #
#                                Eric Rado                                 #
#                                                                          #
############################################################################

from socket import *
from threading import *
import queue
import sys
import traceback
import errno
import sys
import copy
import random
import pickle
import time
###################################
##      CHAT GLOBAL VARIABLES    ##
###################################
onlineUsers = {}
teams = {}
hostname = 'localhost'
ftpPort = 13000
udpPort = 12000
messageLog = queue.LifoQueue()

###################################
##  BATTLESHIP GLOBAL VARIABLES  ##
###################################
BUFFER_SIZE = 5052
all_boards = {}
tcpUsers = {}
NUMBER_OF_PLAYERS_REQUIRED = 4
players_connected_counter = 0
players_ready = 0
playersTurn = 0
lock = Lock()
#add empty string to turn list which will later be used in a
#assign turn to players function
playersTurnList = []
for i in range (4):
    playersTurnList.append('')

ships = {
        "Aircraft Carrier":5,
        "Battleship":4,
        "Submarine":3,
        "Destroyer":3,
        "Patrol Boat":2
        }

# Blank 10x10 board (-1 represent blank space on board)
board = []
for i in range(10):
    board_row = []
    for j in range(10):
        board_row.append(-1)
    board.append(board_row)

########################################################################
##                            CHAT THREAD                             ##
########################################################################

class ChatThread(Thread):
    def __init__(self,udpSock,tcpSock,tcpAddr,udpAddr):
        Thread.__init__(self)
        #THREAD LOCAL VARIABLES
        self.udpSock = udpSock
        self.tcpSock = tcpSock
        self.username = ''
        self.online = False
        self.teamColor = ''
        self.tcpAddr = tcpAddr
        self.udpAddr = udpAddr
        self.addrCheck = 0
        self.lock = Lock()

    def runCmds(self):
        global messageLog

        self.lock.acquire()
        #acquiring message from global messageLog queue
        try:
            message = messageLog.get()
        finally:
            self.lock.release()

        tokens = message.split()
        #if message is empty it will not send to anyone
        if(len(tokens) == 2):
            return None

        #parsing user and option from message
        user = tokens[0]
        option = tokens[2]

        #to logout
        if(option.upper() == '!Q'):
            self.logout(user)

        #send user list of current online users
        elif(option.upper() == 'LIST'):
            self.printOnlineUsers(user)

        #send a message to a particular team
        elif(option == '@'):
            if(tokens[3] != 'red' or tokens[3] != 'blue'):
                color = self.teamColor
            else:
                color = tokens[3]
            self.teamBroadcast(user,color,message)

        #initial message to test connection,does not broadcast
        elif(option == 'CONNECTIONTEST'):
            return None

        #sends message to everyone who is online
        elif(len(tokens) > 2):
            self.broadcast(user,message)

    def logout(self,user):
        global onlineUsers
        global teams
        for key in onlineUsers:
            if(key == user):
                self.udpSock.sendto('quit'.encode(),self.udpAddr)

        #send a message to everyone in server about user going offline
        message = user + ' is now offline.'
        self.broadcast(user,message)
        print(user + " has logged out.")
        #remove user from online dictionary
        del onlineUsers[user]
        del teams[user]
        print(onlineUsers)

    def printOnlineUsers(self,user):
        global onlineUsers
        global teams

        message = 'Online Users' + '\n'
        for key in onlineUsers:
            if(key != user):
                team = '\t' +teams[key]
                gamer = key + team +'\n'
                message = message + gamer
        for key in onlineUsers:
            if(key == user):
                addr = onlineUsers[key]
                self.udpSock.sendto(message.encode(),addr)

    def login(self):
        global teams

        while(True):
            self.tcpSock.send('Welcome to Battleship Chat\nEnter username '
                              'and team color red | blue ?\n'
                              'Then press login'.encode())

            #holds username and team
            response = self.tcpSock.recv(1024).decode()
            if(response == 'quit'):
                return None
            tokens = response.split()
            print(tokens)

            #set username and thier corresponding team color
            self.username = tokens[0]
            self.teamColor = tokens[1]
            color = self.teamColor.upper()

            if((color == 'RED') or (color == 'BLUE')):
                break
            else:
                colorMsg = 'Invalid color. Team color red | blue\nPlease try again.\n'
                self.tcpSock.send(colorMsg.encode())

        #set user online
        self.online = True
        teams[self.username] = self.teamColor
        self.tcpSock.send('Logged in.\n'
                          'If you need help with commands type help.'.encode())

    def teamBroadcast(self,user,color,message):
        global teams
        global onlineUsers

        for key in teams:
            if((teams[key] == color) and (key != user)):
                addr = onlineUsers[key]
                self.udpSock.sendto(message.encode(),addr)


    def broadcast(self,user,message):
        global onlineUsers

        #send message to all users except author of the message
        for key in onlineUsers:
            if(key != user):
                addr = onlineUsers[key]
                self.udpSock.sendto(message.encode(),addr)

    def getUdpAddr(self):
        message = self.tcpSock.recv(4096).decode()
        tokens = message.split(',')

        #setting up udp address to store in dictionary
        #obtaining localhost and port number
        localhost = tokens[0][2:-1]
        if(localhost == '0.0.0.0'):
            localhost = 'localhost'
        port = int(tokens[1][1:-1])
        self.udpAddr = (localhost,port)

        #adding user and address to online dictionary and sending
        #all current online users an alert new user online message
        onlineUsers[self.username] = self.udpAddr
        message = self.username + ' has logged on.'
        self.broadcast(self.username,message)
        print(onlineUsers)
        print(teams)
        self.addrCheck = self.addrCheck + 1

    def startPlayer(self):
        global lock,players_connected_counter

        #start a BATTLESHIP player thread
        self.playerServerThread = PlayerThread(self.tcpSock,self.tcpAddr,
                                self.username,self.teamColor)
        self.playerServerThread.start()
        with lock:
            players_connected_counter += 1

        self.addrCheck = self.addrCheck + 1

    def run(self):
        global messageLog
        global onlineUsers

        self.login()
        addrCheck = 0
        #receive incoming messages from chatters and runs commands
        while(self.online):
            #runs if user address has not been stored to dictionary
            if(self.addrCheck == 0):
                self.getUdpAddr()

            #Start a player thread
            if(self.addrCheck == 1):
                self.startPlayer()

            message, addr = self.udpSock.recvfrom(4096)
            modMessage = message.decode()

            #store message to global queue messages
            messageLog.put(modMessage)
            self.runCmds()


########################################################################
##                           PLAYER THREAD                            ##
########################################################################

class PlayerThread(Thread):
    global all_boards, teams, game_not_over

    def __init__(self, connection_socket, address,username,teamColor):

        Thread.__init__(self)
        global tcpUsers

        #local thread variables pertaining to the user
        self.connection_socket = connection_socket
        self.addr = address
        self.username = username
        self.player_port = self.addr[1]
        self.team = teamColor
        self.player_board = None
        self.turn = 0

        tcpUsers[self.username] = self.connection_socket

    def run(self):
        global all_boards, teams,lock,NUMBER_OF_PLAYERS_REQUIRED
        global players_connected_counter,players_ready,playersTurn

        # BATTLESHIPS GAME PLAY LOGIC
        print("Waiting for more players to connect...")

        #sends msg to clients if not enough players connected
        if(players_connected_counter != NUMBER_OF_PLAYERS_REQUIRED):
            self.connection_socket.send('Waiting for more players to connect...'.encode())
        while(True):
            if(players_connected_counter == NUMBER_OF_PLAYERS_REQUIRED):
                break
        self.connection_socket.send('Ready'.encode())

        print('Enough players connected, time to setup turns boards...')

        #sets the turn for all connected players
        self.turn_setup()

        #player sets up their board
        self.player_setup()

        #Waits for all players to setup their boards before the game is started
        if(players_ready != NUMBER_OF_PLAYERS_REQUIRED):
            self.connection_socket.send('Waiting for all players to set'
                        ' their boards...'.encode())
        while(True):
            if(players_ready == NUMBER_OF_PLAYERS_REQUIRED ):
                break

        self.connection_socket.send('All players have finnaly setup their boards.'.encode())


        #At this point all players are connected and their boards are setup.
        #Everyone is ready to play.
        try:
            # GAME RUNNING LOOP
            while True:
                if(self.turn != playersTurn ):
                    time.sleep(2)
                    self.connection_socket.send('Please wait for your turn...'.encode())
                    while(True):
                        if(self.turn == playersTurn):
                            break

                self.connection_socket.send('It is now your turn...'.encode())

                time.sleep(8)
                self.send_updated_game_info()

                # Get command from user to play
                cmd = self.connection_socket.recv(BUFFER_SIZE).decode()
                tokens = cmd.split()

                # set parameter that will be passed to user move function
                if(len(tokens) == 3):
                    target = tokens[0]
                    x = int(tokens[1])
                    y = int(tokens[2])

                #If player inputs QUIT
                if (tokens[0].upper() == 'QUIT'):
                    msg = self.username + " quit the game."
                    self.tcpBroadcast(msg)
                    # all players must agree
                    return None

                # Attack opponent
                result = self.user_move(target,x,y)

                with lock:
                    if((playersTurn + 1)== NUMBER_OF_PLAYERS_REQUIRED):
                        playersTurn = 0
                    else:
                        playersTurn += 1

                if (result == "WIN"):
                    print(self.username + " won!")
                    print("Game over")
                    return None

        except OSError as e:
            # A socket error
              print("Socket error:",e)


    ######################################
    ##          GAME FUNCTIONS          ##
    ######################################

    def player_setup(self):

        global teams,players_ready,lock,all_boards

        # Receive board from user after he/she places the ships
        print ("Waiting for player to place ships and return board....")
        self.player_board = pickle.loads(self.connection_socket.recv(BUFFER_SIZE))
        print ("Player board received....")
        print ("(" + self.username + ") has positioned his ships on his board.")


        # Add player board to set of all boards
        with lock:
            all_boards[self.username] = self.player_board

        print("(" + self.username + ") is all setup and ready to play.")

        #lock players_ready variable so one user who finished setting up their
        #board increases the counter
        with lock:
            players_ready += 1

    def turn_setup(self):
        global lock,playersTurnList

        #assign player a turn
        with lock:
            if(self.team.upper() == 'RED'):
                if(not playersTurnList[0]):
                    self.turn = 0
                    playersTurnList[0] = self.username
                    print(self.username + ' ' + str(self.turn))

                elif(not playersTurnList[2]):
                    self.turn = 2
                    playersTurnList[2] = self.username
                    print(self.username + ' ' + str(self.turn))

            elif(self.team.upper() == 'BLUE'):
                if(not playersTurnList[1]):
                    self.turn = 1
                    playersTurnList[1] = self.username
                    print(self.username + ' ' + str(self.turn))

                elif(not playersTurnList[3]):
                    self.turn = 3
                    playersTurnList[3] = self.username
                    print(self.username + ' ' + str(self.turn))

    def tcpBroadcast(self,msg):
        global tcpUsers

        if(self.team.upper() == 'RED'):
            sendMsg = msg + '\n' + 'Team BLUE wins.'
        else:
            sendMsg = msg +'\n' + 'Team RED wins.'

        for key in tcpUsers:
            if(key != self.username):
                sock = tcpUsers[key]
                sock.send('MATCH IS OVER.'.encode())
                sock.send(sendMsg.encode())


    #Sends players an updated board and list of all online players
    def send_updated_game_info(self):
        global all_boards,teams
        # Send all boards

        print("SENDING ALL BOARDS")
        self.connection_socket.send( pickle.dumps(all_boards) )

        # Send updated list of active players
        print("Sending list of players...")
        self.connection_socket.send( pickle.dumps(teams) )
        print("List of players sent.")



    def user_move(self,targetted_player,x,y):
        global all_boards

        print(targetted_player + " is being targeted by team " + self.team.upper())
        print("x = ", x)
        print("y = ", y)

        # if move is a hit, check ship sunk and win condition
        res = self.make_move(all_boards[targetted_player],x,y)

        # Check result
        if res == "hit":
            msg = "Hit at " + str(x+1) + "," + str(y+1)
            print(msg)
            self.connection_socket.send(msg.encode())
            self.check_sink(all_boards[targetted_player],x,y)
            all_boards[targetted_player][x][y] = '$'

            # Check whether there is a winner
            if self.check_win(all_boards[targetted_player]):
                msg = "WIN"
                self.connection_socket.send(msg.encode())
                return msg

            return msg

        elif res == "miss":
            msg = "Sorry, " + str(x+1) + "," + str(y+1) + " is a miss."
            print(msg)
            self.connection_socket.send(msg.encode())
            all_boards[targetted_player][x][y] = "*"
            return msg
        elif res == "try again":
            msg = "Sorry, that coordinate was already hit. Please try again"
            print(msg)

            self.connection_socket.send(msg.encode())
            return msg
        else:
            msg = "try again"
            print(msg)
            self.connection_socket.send(msg.encode())
            return msg



    def make_move(self,board,x,y):

        #make a move on the board and return the result, hit, miss or try again for repeat hit
        if board[x][y] == -1:
            return "miss"
        elif (board[x][y] == '*' or board[x][y] == '$'):
            return "try again"
        else:
            return "hit"


    def check_sink(self,board,x,y):

        #figure out what ship was hit

        if board[x][y] == "A":
            ship = "Aircraft Carrier"
        elif board[x][y] == "B":
            ship = "Battleship"
        elif board[x][y] == "S":
            ship = "Submarine"
        elif board[x][y] == "D":
            ship = "Destroyer"
        elif board[x][y] == "P":
            ship = "Patrol Boat"

        board[-1][ship] -= 1

        if board[-1][ship] == 0:
            print( ship + " Sunk" )


    def check_win(self,board):

        #simple for loop to check all cells in 2d board
        #if any cell contains a char that is not a hit or a miss return false
            for i in range(10):
                for j in range(10):
                    if board[i][j] != -1 and board[i][j] != '*' and board[i][j] != '$':
                        return False
            return True

#-------------------------| END OF PLAYER THREAD CLASS |-------------------------------#

def main():
    global hostname
    global ftpPort
    global udpPort
    global players_connected_counter

    udpAddr = (hostname,udpPort)
    #setting up server tcp socket
    tcp = socket(AF_INET,SOCK_STREAM)
    tcp.setsockopt(SOL_SOCKET,SO_REUSEADDR,1)
    tcp.bind((hostname,ftpPort))

    #setting up server udp socket
    udp = socket(AF_INET,SOCK_DGRAM)
    udp.setsockopt(SOL_SOCKET,SO_REUSEADDR,1)
    udp.bind(udpAddr)

    threads = []
    while(True):
        print('Listening for chatters...')
        tcp.listen(10)
        conn, tcpAddr = tcp.accept()
        chat = ChatThread(udp,conn,tcpAddr,udpAddr)
        chat.start()
        threads.append(chat)


main()
