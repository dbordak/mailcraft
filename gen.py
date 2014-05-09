#!/bin/python2

from pymclevel.materials import alphaMaterials
from pymclevel import mclevel, nbt
from getmail import getmail
import random
from os import path
from shutil import copytree

# TODO:
# * Add more roomtypes (other than jumping puzzles).
# * Change pillar_room from a map object to a function.
#  * Maybe also same thing with tall_room
# * Change SetExits so that it can add, remove, or ignore exits -- or
#    so that it can add doors.
# * Replace lava and pit with single dangerous room function.
# * Rotated dangerfloors for message threads.
# * Fix sign-laying function.
# * Alternate route in case of impossible jumping puzzle.
# * Color-coded treasure rooms.
# * Improve readability of setExits.
# * Switch ordering of main loop (rooms before tunnels).

HEIGHT_INC = 8
STONE_BRICK = 98
difficulty = [1, 2, 3, 4, 5, 7]
length = [7, 12, 20, 30, -1]


# Simple wrapper which returns the created chunk
def makeChunk(world, col, row):
    world.createChunk(col, row)
    return world.getChunk(col, row)


def wipeChunk(chunk):
    chunk.Blocks[:, :, :] = 0
    chunk.Data[:, :, :] = 0
    chunk.chunkChanged()
    return chunk


def roomCopy(fro, to, h):
    to.Blocks[:, :, 3+h:] = fro.Blocks[:, :, 3:256-h]
    to.Data[:, :, 3+h:] = fro.Data[:, :, 3:256-h]
    to.chunkChanged()
    return to


def deepCopy(fro, to):
    to.Blocks[:, :, :] = fro.Blocks[:, :, :]
    to.Data[:, :, :] = fro.Data[:, :, :]
    to.chunkChanged()
    return to


def placeNextRoom(room, seed, h, roomArray):
    random.seed(seed)
    i = random.randint(0, len(roomArray)-1)
    roomCopy(roomArray[i], room, h)
    j = random.randint(0, 10)
    if j == 0:
        makePillar(room)
    # if j==1:
    #     makeTall(room)
    return room


# -1 = ignore
# 0  = wall
# 1  = door
def setExits(room, h, west=-1, east=-1, north=-1, south=-1):
    floor_mat = alphaMaterials.Cobblestone.ID
    wall_mat = alphaMaterials.StoneBricks.ID
    floor = 3+h

    if west > -1:
        if west == 1:
            l_block = 0
            room.Blocks[0, 7:9, floor] = floor_mat
        else:
            l_block = wall_mat
        room.Blocks[0, 7:9, floor+1:floor+3] = l_block

    if east > -1:
        if east == 1:
            r_block = 0
            room.Blocks[15, 7:9, floor] = floor_mat
        else:
            r_block = wall_mat
        room.Blocks[15, 7:9, floor+1:floor+3] = r_block

    if north > -1:
        if north == 1:
            t_block = 0
            room.Blocks[7:9, 0, floor] = floor_mat
        else:
            t_block = wall_mat
        room.Blocks[7:9, 0, floor+1:floor+3] = t_block

    if south > -1:
        if south == 1:
            b_block = 0
            room.Blocks[7:9, 15, floor] = floor_mat
        else:
            b_block = wall_mat
        room.Blocks[7:9, 15, floor+1:floor+3] = b_block

    room.chunkChanged()
    return room


def dangerFloor(room, h, dangerBlock, current_difficulty):
    room.Blocks[:, :, :4+h] = alphaMaterials.StoneBricks.ID
    room.Blocks[1:15, 2:14, :4+h] = dangerBlock
    room.ChunkChanged()
    return room


def theFloorIsLava(room, h):
    room.Blocks[:, :, 2+h:4+h] = alphaMaterials.StoneBricks.ID # Create retaining area
    room.Blocks[1:15, 2:14, 3+h] = 10  # Add lava
    room.chunkChanged()
    return room


def noFloor(room, h):
    room.Blocks[:, :, :4+h] = alphaMaterials.StoneBricks.ID # Create walls
    room.Blocks[1:15, 2:14, :4+h] = 0  # Remove floor
    room.chunkChanged()
    return room


def floorPuzzle(room, h, dangerBlock, diff):
    for i in xrange(2, 14):
        for j in xrange(1, 15):
            k = random.randint(0, diff)
            if k == 0:
                room.Blocks[j, i, 3+h] = 1
            else:
                room.Blocks[j, i, 3+h] = dangerBlock


def makePillar(room):
    room.Blocks[3:5, 3:5, :] = alphaMaterials.StoneBricks.ID
    room.Blocks[3:5, 11:13, :] = alphaMaterials.StoneBricks.ID
    room.Blocks[11:13, 3:5, :] = alphaMaterials.StoneBricks.ID
    room.Blocks[11:13, 11:13, :] = alphaMaterials.StoneBricks.ID
    room.chunkChanged()
    return room


# sets all signs in chunk to text
def setSign(room, text=['', '', '', '']):
    for tileEntity in room.TileEntities:
        print tileEntity
        # if tileEntity["id"].value == "Sign":
        #     for i in range(4):
        #         tileEntity["Text{0}".format(i + 1)].value = text[i]
    return room


def main():
    difficulty_setting = difficulty[3]  # Range is 0 - 5
    length_setting = length[2]  # Range is 0 - 4

    copytree("DungeonBase", "Dungeon")

    blockLevel = mclevel.fromFile(path.join("DungeonBlocks", "level.dat"))

    rooms = {
        "start": blockLevel.getChunk(0, 0),
        "v_tunnel": blockLevel.getChunk(0, 1),
        "basic": blockLevel.getChunk(0, 2),
        "basic2": blockLevel.getChunk(1, 2),
        "stairs": blockLevel.getChunk(1, 1),
        "h_tunnel": blockLevel.getChunk(2, 1),
        "treasure": blockLevel.getChunk(3, 0),
        "gaudy": blockLevel.getChunk(4, 0),
        "end": blockLevel.getChunk(2, 0)
    }
    # Big room is in 6,0; 7,0; and 7,1.

    room_sel = [rooms["basic"], rooms["basic2"]]

    level = mclevel.fromFile(path.join("Dungeon", "level.dat"))

    row_num = 0
    col_num = 0
    height = 0

    deepCopy(rooms["start"], makeChunk(level, col_num, row_num))
    row_num += 1

    print 'Fetching mail...'
    maildata = getmail()
    print 'Mail fetched. Building world...'
    # print maildata

    for i, thread in enumerate(maildata):
        if i == length_setting:
            break
        r = roomCopy(rooms["v_tunnel"], makeChunk(level, 0, row_num), height)

        point = [6, 5+(int)(i/5)*HEIGHT_INC, 30+32*i]
        # # Only works when not a staircase -- for now.
        # point=[6, 5+height, 30+32*i]
        tileEntity = level.tileEntityAt(6, 5+(int)(i/5)*HEIGHT_INC, 30+32*i)

        linekeys = ["Text" + str(k) for k in xrange(1, 5)]

        if not tileEntity:
            tileEntity = nbt.TAG_Compound()
            tileEntity["id"] = nbt.TAG_String("Sign")
            tileEntity["x"] = nbt.TAG_Int(point[0])
            tileEntity["y"] = nbt.TAG_Int(point[1])
            tileEntity["z"] = nbt.TAG_Int(point[2])
            for l in linekeys:
                tileEntity[l] = nbt.TAG_String("")

        subject = "Draft"
        fro = ""
        if thread:
            subject = thread[0]['subject'][:15]
            fro = thread[0]['from'][:15]
        tileEntity[linekeys[0]] = subject
        tileEntity[linekeys[1]] = fro

        level.addTileEntity(tileEntity)
        r.chunkChanged()

        diffInterval = int(length_setting/difficulty_setting)
        if i % diffInterval == 0 and i != 0 and i != length_setting:
            roomCopy(rooms["stairs"], r, height)
            height += HEIGHT_INC
        else:
            roomCopy(rooms["v_tunnel"], r, height)
        # setSign(level.getChunk(2+col_num, 2+row_num), ['ffff','hh','',''])
        row_num += 1
        # T-room
        original_col_number = col_num
        if len(fro):
            seed = fro
        else:
            seed = random.random()
        r = placeNextRoom(makeChunk(level, col_num, row_num), seed, height,
                          room_sel)
        # Open a hole in the right side of rooms when there's another room in
        # the thread.
        if len(thread) > 1:
            setExits(r, height, east=1)
        col_num += 1
        # setSign(level.getChunk(col_num, row_num), ['1','2','3','4'])
        for ii, message in enumerate(thread):
            if ii == 0:
                continue
            roomCopy(rooms["h_tunnel"], makeChunk(level, col_num, row_num),
                     height)
            col_num += 1
            r = placeNextRoom(makeChunk(level, col_num, row_num), seed, height,
                              room_sel)
            setExits(r, height, west=1, east=1, north=0, south=0)
            if height < 24:
                theFloorIsLava(r, height)
                dangerBlock = 10
            else:
                noFloor(r, height)
                dangerBlock = 0
            floorPuzzle(r, height, dangerBlock, (height/HEIGHT_INC)+1)
            col_num += 1
        r = makeChunk(level, col_num, row_num)
        # Close right for last room in a short thread.
        if col_num - original_col_number < 5:
            setExits(level.getChunk(col_num - 1, row_num), height, east=0)
        elif col_num - original_col_number < 8:
            roomCopy(rooms["treasure"], r, height)
        else:
            roomCopy(rooms["gaudy"], r, height)
        if i % 2 == 1:
            r = level.getChunk(0, row_num)
            if height < 16:
                theFloorIsLava(r, height)
                dangerBlock = alphaMaterials.Lava.ID
            else:
                noFloor(r, height)
                dangerBlock = 0
            floorPuzzle(r, height, dangerBlock, (height/HEIGHT_INC)+1)
        row_num += 1
        col_num = original_col_number
    roomCopy(rooms["stairs"], makeChunk(level, 0, row_num), height)
    height += HEIGHT_INC
    row_num += 1
    roomCopy(rooms["end"], makeChunk(level, col_num, row_num), height)

    print 'Built. Saving...'
    level.generateLights(level.allChunks)
    level.saveInPlace()
    print 'Done!'

if __name__ == "__main__":
    main()
