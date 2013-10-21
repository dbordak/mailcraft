#mailcraft
A Minecraft dungeon generator that uses a user's email conversations to create rooms and hallways.

Uses [context.io](http://context.io/) to fetch email data, and [pymclevel](https://github.com/mcedit/pymclevel) to edit Minecraft map files.

The dungeon consists of a straight hallway, leading to a dragon. Along the way are branching hallways, each representing a recent email thread, each consisting of several rooms of stepping puzzles, representing individual emails. At the end of each branching hallway is a treasure room, holding equipment necessary for fighting the dragon.

![alt text](https://raw.github.com/dbordak/mailcraft/master/pic1.png "pic1")
![alt text](https://raw.github.com/dbordak/mailcraft/master/pic2.png "pic2")
![alt text](https://raw.github.com/dbordak/mailcraft/master/pic3.png "pic3")

##Dependencies
The context.io library depends on the python libraries `rauth` and `requests`.

##Usage
Create an account with context.io (make sure to select 2-legged authentication!), then make a file `secrets.py` with your credentials and email:
```
CONSUMER_KEY = 
CONSUMER_SECRET = 
EMAIL = 
```

Run `python gen.py` to generate the dungeon, then copy the `DungeonBase` directory to your Minecraft save location (`~/.minecraft/saves` on Linux, `%APPDATA%\.minecraft\saves\` on Windows, `~/Library/Application Support/minecraft/saves/` on Mac), then open the level in Minecraft.
