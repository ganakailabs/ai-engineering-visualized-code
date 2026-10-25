"""Chapter 15, MM-113: loops, oscillation and drift.

A watchdog reads each step and ends a stuck run with the NO_PROGRESS stop (Chapter 5).
Three shapes of stuck, each checked on what the step did, not on what the model said:
  loop        the same call with the same arguments, `repeat` times in a row
  oscillation the state flips between two values, A B A B, `flips` times
  drift       the distance to the goal grows `drift` steps in a row
"""


class Watchdog:
    def __init__(self, repeat=3, flips=4, drift=3):
        self.repeat, self.flips, self.drift = repeat, flips, drift
        self.calls, self.states, self.dist = [], [], []

    def observe(self, call=None, state=None, distance=None):
        """Feed one step. Returns None, or (reason, detail) to stop on."""
        if call is not None:
            self.calls.append(call)
            last = self.calls[-self.repeat:]
            if len(last) == self.repeat and len(set(last)) == 1:
                return "no_progress", f"loop repeated={call[0]} x{self.repeat}"
        if state is not None:
            self.states.append(state)
            last = self.states[-self.flips:]
            if (len(last) == self.flips and len(set(last)) == 2
                    and all(a != b for a, b in zip(last, last[1:]))):
                return "no_progress", f"oscillation {last[0]}<->{last[1]} x{self.flips}"
        if distance is not None:
            self.dist.append(distance)
            last = self.dist[-(self.drift + 1):]
            if len(last) == self.drift + 1 and all(b > a for a, b in zip(last, last[1:])):
                return "no_progress", f"drift distance {last[0]}->{last[-1]}"
        return None
