# abuse_detection_steemit

<img src="https://user-images.githubusercontent.com/34451833/39098894-301d39a6-467a-11e8-8b54-a0cc5bc3a262.png">

This bot is a steem blockchain listener that stores data on last day upvotes (generally regarded to be reward pool abuse), it keeps track of who is distributing the most last day upvotes, who is recieving the most money from last day votes and how many unique accounts are voting on each users post. Data then graphically represented in pie charts.

[Windows executable](https://mega.nz/#!goI0HTxR!dwRpVTFCtvOOIOXrBtY_WKUUCmPVb23Qx-gx9Anx5lA)

[Logos](https://drive.google.com/drive/folders/16eNXnl2ZVuabuTNiuJiWsGc-SCjfFv0J)

### Installation Instructions
1) Download the file named `slve-x.whl`
2) Open the console and run the command `python -m pip install slve-x.whl`

### Useage
Type `from slve import abuse_detection_steemit` to run the streamer
Type `from slve import make_pie` to generate the pie charts. *Note that this requires an IPython console.*