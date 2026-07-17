# Visual Language

Pad-Lattice uses shape plus color so the surface is readable without relying on
color alone.

## 8x8 Matrix

The diagrams below show the Launchpad Pro Mk1 programmer grid as the device
faces you. Pad `11` is bottom left and pad `88` is top right.

### Note Numbers

<div className="matrixDiagram" aria-label="Launchpad Pro Mk1 note number map">
  <div className="matrixGrid">
    <span className="matrixCell note">81</span><span className="matrixCell note">82</span><span className="matrixCell note">83</span><span className="matrixCell note">84</span><span className="matrixCell note">85</span><span className="matrixCell note">86</span><span className="matrixCell note">87</span><span className="matrixCell note">88</span>
    <span className="matrixCell note">71</span><span className="matrixCell note">72</span><span className="matrixCell note">73</span><span className="matrixCell note">74</span><span className="matrixCell note">75</span><span className="matrixCell note">76</span><span className="matrixCell note">77</span><span className="matrixCell note">78</span>
    <span className="matrixCell note">61</span><span className="matrixCell note">62</span><span className="matrixCell note">63</span><span className="matrixCell note">64</span><span className="matrixCell note">65</span><span className="matrixCell note">66</span><span className="matrixCell note">67</span><span className="matrixCell note">68</span>
    <span className="matrixCell note">51</span><span className="matrixCell note">52</span><span className="matrixCell note">53</span><span className="matrixCell note">54</span><span className="matrixCell note">55</span><span className="matrixCell note">56</span><span className="matrixCell note">57</span><span className="matrixCell note">58</span>
    <span className="matrixCell note">41</span><span className="matrixCell note">42</span><span className="matrixCell note">43</span><span className="matrixCell note">44</span><span className="matrixCell note">45</span><span className="matrixCell note">46</span><span className="matrixCell note">47</span><span className="matrixCell note">48</span>
    <span className="matrixCell note">31</span><span className="matrixCell note">32</span><span className="matrixCell note">33</span><span className="matrixCell note">34</span><span className="matrixCell note">35</span><span className="matrixCell note">36</span><span className="matrixCell note">37</span><span className="matrixCell note">38</span>
    <span className="matrixCell note">21</span><span className="matrixCell note">22</span><span className="matrixCell note">23</span><span className="matrixCell note">24</span><span className="matrixCell note">25</span><span className="matrixCell note">26</span><span className="matrixCell note">27</span><span className="matrixCell note">28</span>
    <span className="matrixCell note">11</span><span className="matrixCell note">12</span><span className="matrixCell note">13</span><span className="matrixCell note">14</span><span className="matrixCell note">15</span><span className="matrixCell note">16</span><span className="matrixCell note">17</span><span className="matrixCell note">18</span>
  </div>
</div>

### Multi-Agent Surface

The top six rows show the selected session. The next row retains the state of
each visible session, and the bottom row combines direct actions with session
selectors.

<div className="matrixDiagram" aria-label="Current Pad-Lattice action and state layout">
  <div className="matrixGrid">
    <span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span>
    <span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span>
    <span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell state">state</span><span className="matrixCell state">state</span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span>
    <span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell state">state</span><span className="matrixCell state">state</span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span>
    <span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span>
    <span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell idle"></span>
    <span className="matrixCell idle"></span><span className="matrixCell idle"></span><span className="matrixCell statusBlue">S1<br />23</span><span className="matrixCell statusWhite">S2<br />24</span><span className="matrixCell statusYellow">S3<br />25</span><span className="matrixCell statusGreen">S4<br />26</span><span className="matrixCell idle"></span><span className="matrixCell idle"></span>
    <span className="matrixCell approve">approve<br />11</span><span className="matrixCell reject">reject<br />12</span><span className="matrixCell accentOne">A1<br />13</span><span className="matrixCell accentTwo">A2<br />14</span><span className="matrixCell accentThree">A3<br />15</span><span className="matrixCell accentFour">A4<br />16</span><span className="matrixCell retry">retry<br />17</span><span className="matrixCell stop">stop<br />18</span>
  </div>
</div>

Pads `13` through `16` select up to four visible agent sessions:

| `11` | `12` | `13` | `14` | `15` | `16` | `17` | `18` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| approve | reject | agent 1 | agent 2 | agent 3 | agent 4 | retry | stop |

Each occupied selector keeps its slot accent color. Brightness indicates the
selected session. Pads `23` through `26` independently retain each session's
semantic state, so a background approval request remains visible.

### State Examples

<div className="stateExampleGrid">
  <div>
    <p><strong>Waiting for reply</strong></p>
    <div className="miniMatrix" aria-label="Waiting for reply question mark shape">
      <span></span><span></span><span className="white"></span><span className="white"></span><span className="white"></span><span></span><span></span><span></span>
      <span></span><span className="white"></span><span></span><span></span><span></span><span className="white"></span><span></span><span></span>
      <span></span><span></span><span></span><span></span><span className="white"></span><span></span><span></span><span></span>
      <span></span><span></span><span></span><span className="white"></span><span></span><span></span><span></span><span></span>
      <span></span><span></span><span></span><span className="white"></span><span></span><span></span><span></span><span></span>
      <span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span>
      <span></span><span></span><span></span><span className="white"></span><span></span><span></span><span></span><span></span>
      <span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span>
    </div>
  </div>
  <div>
    <p><strong>Waiting for approval</strong></p>
    <div className="miniMatrix" aria-label="Waiting for approval compact yellow exclamation mark">
      <span></span><span></span><span></span><span className="yellow"></span><span className="yellow"></span><span></span><span></span><span></span>
      <span></span><span></span><span></span><span className="yellow"></span><span className="yellow"></span><span></span><span></span><span></span>
      <span></span><span></span><span></span><span className="yellow"></span><span className="yellow"></span><span></span><span></span><span></span>
      <span></span><span></span><span></span><span className="yellow"></span><span className="yellow"></span><span></span><span></span><span></span>
      <span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span>
      <span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span>
      <span></span><span></span><span></span><span className="yellow"></span><span className="yellow"></span><span></span><span></span><span></span>
      <span className="approve"></span><span className="reject"></span><span></span><span></span><span></span><span></span><span className="retry"></span><span className="stop"></span>
    </div>
  </div>
  <div>
    <p><strong>Success</strong></p>
    <div className="miniMatrix" aria-label="Success green happy face">
      <span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span>
      <span></span><span></span><span className="green"></span><span></span><span></span><span className="green"></span><span></span><span></span>
      <span></span><span></span><span className="green"></span><span></span><span></span><span className="green"></span><span></span><span></span>
      <span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span>
      <span></span><span className="green"></span><span></span><span></span><span></span><span></span><span className="green"></span><span></span>
      <span></span><span></span><span className="green"></span><span className="green"></span><span className="green"></span><span className="green"></span><span></span><span></span>
      <span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span>
      <span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span>
    </div>
  </div>
</div>

## States

| Pad color | Agent state | Meaning |
| --- | --- | --- |
| Blue | `running` | Codex is working. |
| White `?` | `waiting_for_reply` | Codex is waiting for a user reply. |
| White line | `user_typing` | Reserved for integrations that can observe live typing. |
| Yellow `!` | `waiting_for_approval` | Approval or review is needed. |
| Green happy face | `success` | Completed successfully; then returns to waiting. |
| Red X | `error` | Failed; then returns to waiting. |

## Controls

| Pad | Action | Use |
| --- | --- | --- |
| `11` | `approve` | Yes, approve, continue. |
| `12` | `reject` | No, reject, do not proceed. |
| `17` | `retry` | Try again. |
| `18` | `stop` | Stop or interrupt. |

Actions are bright only when the selected session has a connected subscriber
for that capability. Dim pads are mapped but unavailable; pressing one does
not broadcast an action.

## Session Indicators

| Pads | Role |
| --- | --- |
| `13`-`16` | Accent-colored agent selectors; bright means selected. |
| `23`-`26` | Semantic state colors for those four slots. |

## Grid map

Launchpad Pro Mk1 programmer-grid note numbers in table form:

|  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `81` | `82` | `83` | `84` | `85` | `86` | `87` | `88` |
| `71` | `72` | `73` | `74` | `75` | `76` | `77` | `78` |
| `61` | `62` | `63` | `64` | `65` | `66` | `67` | `68` |
| `51` | `52` | `53` | `54` | `55` | `56` | `57` | `58` |
| `41` | `42` | `43` | `44` | `45` | `46` | `47` | `48` |
| `31` | `32` | `33` | `34` | `35` | `36` | `37` | `38` |
| `21` | `22` | `23` state 1 | `24` state 2 | `25` state 3 | `26` state 4 | `27` | `28` |
| `11` approve | `12` reject | `13` agent 1 | `14` agent 2 | `15` agent 3 | `16` agent 4 | `17` retry | `18` stop |
