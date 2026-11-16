# Threefold

A three-of-a-kind memory card game for the browser, played on a 3D table against computer opponents.
The cards are themed on the chakras and the seven rays.

## Playing it

The game is a static web page with no build step. It has to be served over HTTP, because browsers block
the 3D view from loading its images and video when `index.html` is opened straight from disk.

- **GitHub Pages:** in the repository settings, turn on Pages for the `main` branch. The game is then at the Pages address.
- **On your own computer:** run `python3 -m http.server` in this folder and open `http://localhost:8000`.

## Playing online with voice chat

Choose **Multiplayer** in the start menu. One person hosts and gets a five-character room code and an invite
link; friends join with either. Everyone hears everyone through an open microphone with a mute button, and
computer players fill any empty seats. Up to six people can play.

- **The site must use HTTPS.** Browsers only allow microphones on secure pages.
- **If the game sits inside another page in an iframe**, the iframe needs `allow="microphone"`.
- **How players connect:** browsers connect directly to each other with WebRTC, using the
  [PeerJS](https://peerjs.com) library. A meeting-point server introduces them by room code, after which moves and
  voices travel between the players. The host's browser runs the game, so if the host leaves, the game ends.
  If a guest leaves, a computer player takes their seat.
- **The meeting-point server:** by default this is the free public PeerJS server, which needs no account but comes
  with no uptime guarantee. To run your own, start the official PeerServer (for example
  `docker run -p 9000:9000 -d peerjs/peerjs-server`), put it behind HTTPS, and set `server` in the `NET_CONFIG`
  block of `index.html`, for example `{ host: 'peer.heartcenter.org', port: 443, path: '/', secure: true }`.
- **Voice relays:** players on strict networks (some offices and schools) may need a TURN relay to hear each
  other. PeerJS's defaults include public ones; your own can be listed in `iceServers` in `NET_CONFIG`.
- **Fair play:** every player's browser receives the whole table, including face-down cards, so a player who
  opens the browser's developer tools could see cards they shouldn't. It is built for games among friends.

The copy of the game hosted on claude.ai cannot use microphones or outside servers, so multiplayer is switched off there.

## What is here

| Path | What it is |
|---|---|
| `index.html` | The game: rules, computer players, 3D table, menus and effects, all in one file. |
| `assets/` | Images and video used by the game: table, floor, rug, room reflections, card stock, chakra emblems, the Holy Spirit video. |
| `flat.html` | The first, flat 2D version of the game. It needs nothing from `assets/`. |
| `tools/render_glb.py` | Turns a `.glb` 3D model into the flat emblem picture used on a card. |

## Changing the cards

Card names, colours, emblems, backgrounds and fire colours are set near the top of the script in `index.html`,
in the `CARD_FACES` block. Timing, difficulty, fonts and the room's surfaces are set in the blocks around it.

To add an emblem from a 3D model (needs Python with numpy, Pillow and OpenCV):

```
python3 tools/render_glb.py model.glb emblem.png front unlit
```

Save the result into `assets/` and point the card's `emblem` at it.

## Rules

36 cards: three copies of each number from 1 to 12. Every hand is sorted from lowest to highest.
On your turn, reveal cards one at a time: any face-down middle card, or the lowest or highest hidden card
in any hand, including your own. A mismatch ends your turn and the cards go back. Three of a kind is a trio,
which you keep.

- **Simple mode:** win with any three trios.
- **Spicy mode:** win with two connected trios, whose numbers add up to 7 or differ by 7.
- The trio of 7s wins at once in either mode.

The three-of-a-kind mechanics follow the card game Trio by Kaya Miyano. This project is not affiliated with or endorsed by its publishers.
