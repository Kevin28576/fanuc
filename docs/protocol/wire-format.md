# Wire format

What strings Python sends the controller, how it knows when it's
received a full response, how it detects the driver version.

## Basic format

```
sent:      <command>[:<param>...]\n
received:  <code>:<message>
```

Code `0` is success, `1` is failure.

Two easy things to trip on:

- The command sent has to end in a newline; the driver's
  `READ comm_file(cmd)` reads line by line.
- The response has no terminator character. `WRITE comm_file (resp)`
  in `mappdk_server.kl` doesn't send a CR; the only boundary is the
  TCP packet boundary. Upstream therefore only calls `recv()` once, so
  a response split across packets reads as truncated. Here the
  protocol layer tells the transport layer whether it's "received
  enough yet"; if not, it keeps reading, see
  `transport.MappdkTransport._recv`.

When a connection is established, the driver sends a `0:success`
first (in `OPEN_COMM`, `mappdk_comm.kl`), which has to be read and
discarded, or it gets mistaken for the response to the next command.

## Motion command field widths

```
movej:VVVV:AAAA:CCC:M:N:<value1>:<value2>...
       │    │    │  │ └ axis count, 1 digit
       │    │    │  └ 0=joint interpolation 1=linear interpolation
       │    │    └ CNT, 3 digits
       │    └ acceleration, 4 digits
       └ velocity, 4 digits
```

Each value is a sign plus a 13-character fixed-point number, 14
characters total, e.g. `+000090.000000`. The 13-character width is 6
integer digits + decimal point + 6 fraction digits, not the integer
digit count; easy to misread.

## Version detection

`FanucRobot.connect()` sends `ver`. The upstream driver replies
`wrong-command`, at which point `robot.extended` is set to `False`,
and calling an extended method afterward states the reason directly;
the RDO number limit switches accordingly too.

## A latent packet-boundary issue

`transport.py`'s original default `is_complete` only checked "is there
a colon", so a message long enough to happen to land right on a TCP
packet boundary could be judged complete too early, leaking leftover
bytes into the next response. `_recv` now does a short-timeout extra
read after judging a response complete, to confirm there's no
follow-up data; this costs essentially no time in the normal case.

---
*Last updated: 2026-08-31*
