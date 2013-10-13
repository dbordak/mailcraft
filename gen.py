from pymclevel import mclevel
from getmail import *
import random

level = mclevel.fromFile("DungeonBase/level.dat")

#chunkpositions = list(level.allChunks)
#print chunkpositions

start_block = level.getChunk(5,1)
v_tunnel = level.getChunk(1,0)
#basic_room_1 = level.getChunk(2,0)
#basic_room_2 = level.getChunk(3,0)
#pillar_room = level.getChunk(4,0)
#tall_room = level.getChunk(5,0)
stairs = level.getChunk(1,1)
h_tunnel = level.getChunk(2,1)
treasure_room_gaudy = level.getChunk(3,1)
treasure_room_plain = level.getChunk(4,1)
end_room = level.getChunk(6,1)
# Big room is in 6,0; 7,0; and 7,1.

def pickIndex(seed):
	random.seed(seed)
	return random.randint(2,5)

def replaceChunk(replacee,replacer,h):
	replacee.Blocks[:,:,3+h:] = replacer.Blocks[:,:,3:256-h]
	replacee.Data[:,:,3+h:] = replacer.Data[:,:,3:256-h]
	replacee.chunkChanged()

def deepCopy(replacee,replacer):
	replacee.Blocks[:,:,:] = replacer.Blocks[:,:,:]
	replacee.Data[:,:,:] = replacer.Data[:,:,:]
	replacee.chunkChanged()

def placeFirstRoom(row_num):
	next_room = level.getChunk(0,0+row_num)
	deepCopy(next_room,start_block)

def placeNextRoom(col_num,row_num,seed,h):
	next_room = level.getChunk(col_num,row_num)
	i = pickIndex(seed)
	roomtype = level.getChunk(i,0)
	replaceChunk(next_room,roomtype,h)
	return next_room

def placeVerTunnel(row_num,h):
	next_room = level.getChunk(0,row_num)
	replaceChunk(next_room,v_tunnel,h)

def placeHorizTunnel(col_num,row_num,h):
	next_room = level.getChunk(col_num,row_num)
	replaceChunk(next_room,h_tunnel,h)

def placeStair(row_num,h):
	next_room = level.getChunk(0,row_num)
	replaceChunk(next_room,stairs,h)

def increaseHeight(row_num,h):
	placeStair(row_num,h)
	return h+8

def makeHole(room,h):
	room.Blocks[15,7:9,4+h:6+h] = 0 # Remove square-shaped hole
	room.Blocks[15,7:9,3+h] = 4     # Replace floor with cobblestone
	room.chunkChanged()

def convertRoom(room,h):
	room.Blocks[0,7:9,4+h:6+h] = 0 # Same as makeHole, but on the left side
	room.Blocks[0,7:9,3+h] = 4     # Ditto.
	room.Blocks[7:9,0,4+h:6+h] = 98  # Fill doorway in with stone bricks
	room.Blocks[7:9,15,4+h:6+h] = 98 # Ditto.
	makeHole(room,h)

def theFloorIsLava(room,h):
	room.Blocks[:,:,2+h:4+h] = 98 # Create retaining area
	room.Blocks[1:15,1:15,3+h] = 10 # Add lava
	room.chunkChanged()

#sets all signs in chunk to text
def setSign(chunkX, chunkY, text=['','','','']):
	print chunkX
	print chunkY
	chunk=level.getChunk(chunkX, chunkY)
	for tileEntity in chunk.TileEntities:
		print tileEntity
		if tileEntity["id"].value == "Sign":
			for i in range(4):
				tileEntity["Text{0}".format(i + 1)].value = text[i]

def main():
	current_row_number = 0
	current_col_number = 0
	height = 0
	placeFirstRoom(current_row_number)
	current_row_number += 1
	print 'Fetching mail...'
	maildata = getmail()
	print 'Mail fetched. Building world...'
	for i, thread in enumerate(maildata):
		if i==12:
			break

		placeVerTunnel(current_row_number,height)
		#level.saveInPlace()
		#setSign(2+current_col_number, 2+current_row_number, ['ffff','hh','',''])
		current_row_number += 1
		#T-room
		original_col_number=current_col_number
		makeHole(placeNextRoom(current_col_number,current_row_number, random.random(), height), height)
		current_col_number += 1
		#setSign(current_col_number, current_row_number, ['1','2','3','4'])
		for ii, message in enumerate(thread):
			if i==5:
				break

			placeHorizTunnel(current_col_number,current_row_number,height)
			current_col_number += 1
			convertRoom(placeNextRoom(current_col_number, current_row_number, random.random(), height),height)
			current_col_number += 1
		#TODO add treasure room
		current_row_number += 1
		current_col_number=original_col_number
		
	#for i in range(0,5):
		#placeNextRoom(current_col_number,current_row_number,random.random(),height)
		#current_row_number += 1
		#placeVerTunnel(current_row_number,height)
		#current_row_number += 1
	#setSign(2,2, ['1','2','3','4'])
	print 'Built. Saving...'
	level.saveInPlace()
	print 'Done!'

if __name__ == "__main__":
	main()
