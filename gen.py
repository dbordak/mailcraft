#from os import path
from pymclevel import mclevel
#from pymclevel.box import BoundingBox
import random


#fp = path.relpath("DungeonBase")
#print fp
level = mclevel.fromFile("DungeonBase/level.dat")

#chunkpositions = list(level.allChunks)
#print chunkpositions

#box = BoundingBox(origin=[0,0,0],size=[16,256,16])
start_block = level.getChunk(0,0)
v_tunnel = level.getChunk(1,0)
#basic_room_1 = level.getChunk(2,0)
#basic_room_2 = level.getChunk(3,0)
#pillar_room = level.getChunk(4,0)
#tall_room = level.getChunk(0,1)
stairs = level.getChunk(1,1)
h_tunnel = level.getChunk(2,1)

#ChunkIt = base.getChunkSlices(box)
#ChunknItUp = copy.getChunkSlices(box)
#for (chunk,slices,point) in ChunkIt:
#	print "anything"
#	for (c2,s2,p2) in ChunknItUp:
#		c2.Blocks[s2] = chunk.Blocks[slices]
#		c2.Data[s2]   = chunk.Data[slices]
#		c2.chunkChanged()
	#chunkC.Blocks[slices] = chunk.Blocks[slices]
	#chunkC.Data[slices] = chunk.Data[slices]

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
	next_room = level.getChunk(2,2+row_num)
	deepCopy(next_room,start_block)

def placeNextRoom(row_num,seed,h):
	next_room = level.getChunk(2,2+row_num)
	i = pickIndex(seed)
	roomtype = level.getChunk((i%5),(i/5))
	replaceChunk(next_room,roomtype,h)

def placeVerTunnel(row_num,h):
	next_room = level.getChunk(2,2+row_num)
	replaceChunk(next_room,v_tunnel,h)

def placeHorizTunnel(col_num,row_num,h):
	next_room = level.getChunk(2+col_num,2+row_num)
	replaceChunk(next_room,h_tunnel,h)

def placeStair(row_num,h):
	next_room = level.getChunk(2,2+row_num)
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

def main():
	current_row_number = 0
	current_col_number = 0
	height = 0
	placeFirstRoom(current_row_number)
	current_row_number += 1
	placeVerTunnel(current_row_number,height)
	current_row_number += 1
	for i in range(0,5):
		placeNextRoom(current_row_number,random.random(),height)
		current_row_number += 1
		placeVerTunnel(current_row_number,height)
		current_row_number += 1
	level.saveInPlace()

if __name__ == "__main__":
	main()


#for chunk in chunkpositions:
#	print chunk
#	b = level.getChunk(chunk[0],chunk[1])
#	ChunkIt = b.getChunkSlices(box)
#	for (c2, slices, point) in ChunkIt:
#		print c2.Blocks[slices]
#		print c2.Data[slices]
