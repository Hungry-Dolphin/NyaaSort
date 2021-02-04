# NyaaSort

NyaaSort is a Python script for dealing with people who are to lazy to sort their anime.

## Installation

Make sure you have Python > 3.6 since I did not test it on anything else.

Just double-click the NyaaSort.py file and answer the questions it asks you. 

It will automatically add itself to boot-up, if somebody wants me to make that an option instead of a default let me know. 

Note that if you want to use the automatic icon creation you will need to install Pillow and bs4 using pip
## Usage

It will run on boot-up, but you can make it manually run by either double clicking or running it from a terminal. 

Before:

![Before_image](./readme/pre-test.png?raw=true "Before")

After: 

![After image](./readme/default-behavior.png?raw=true "After")

Folder view while using automatic folder icon creation:

![After icon creation](./readme/correct.png?raw=true "After icon creation")

Screenshot of script in action:

![in action](./readme/usage.png?raw=true "Usage")
## Automatic windows folder icon generation
The script itself has been running for quite a while on my pc without any issues, However the automatic icon generation only works half of the time.
This does not prevent the script from working in any way however. 

I will try to make this more consistent, but there is not a lot of documentation on this subject.

An example of unwanted behavior which occurs is when the folder icon only shows up in the detail view.

![bug image](./readme/iffyusage.png?raw=true "Bug")

## Contributing
Pull requests are always welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate, I was not able to upload the anime I used to test the script for obvious reasons, Just add your own to 
```text
integration\fixtures
```

Please don't push to master. I might still approve it if it's a good contribution, but you will make me  cry. 
