# Chapter 4: The Five Wounds

![Glurp stands beside the Book of Wounds, a scroll pinned to the wall with five entries, each marked in red.](../images/04-five-wounds.svg)

Over the following weeks, the tokens kept going. Never all at once, and never in one dramatic gush. They leaked. Like a hoodie snagged on a nail, the pouch was losing them through small tears Glurp could not see.

So Glurp did what careful wizards do. They pinned a long scroll to the wall beside the desk and wrote across the top: *The Book of Wounds*. It was not really a book, and the name was a bit theatrical, but Glurp felt they had earned a bit of theatre. Each time they caught tokens slipping away, they wrote down how. By the end of the month there were five entries, each marked in red.

## The First Wound: The Flood

Glurp asked the agent to run the tests. The agent ran them, which was correct. The tests printed their output, which was also correct. But Glurp's test suite was very chatty. Every passing test announced itself. Every setup step said hello. Somewhere in three thousand lines of cheerful noise, one test had failed, and the agent had to read all three thousand lines to find it.

"It's like lookin' for one wet sock in a river," Glurp wrote. "And payin' for every drop of the river."

They called this **the Flood**: test and build logs that pour into the context and drown the one line that matters.

## The Second Wound: The Circle

One evening the agent hit an error. It tried a fix. The fix failed. It tried the same fix again, and that failed too. It tried a third time with great confidence, as if the third time were a charm. It was not a charm. It tried a fourth time anyway.

Glurp watched it go round and round like a dog after its own tail, and every lap cost tokens.

They called this **the Circle**: a loop that repeats the same failing step and hopes for a different ending.

## The Third Wound: The Forgetful Read

Glurp watched the agent read `config.ork`. A little later it read `config.ork` again. Then once more, to be sure. Then twice more, for luck. Five reads of the same unchanged file, each one paid for in full.

"I do that too," Glurp admitted on the scroll. "Open the fridge, close it, open it again. But the fridge doesn't charge me."

They called this **the Forgetful Read**: the same file, read again and again, when nothing in it has changed.

## The Fourth Wound: The Avalanche

Sometimes one small command brought down an enormous answer. A listing of every file in the valley. A whole database table, dumped. A minified script forty thousand characters long, all on one line. The agent swallowed every bit of it, dutifully, when a handful of lines would have done.

"I asked it what time it was," Glurp wrote, "and it gave me the history of clocks."

They called this **the Avalanche**: giant output that buries the context in one great rumble.

## The Fifth Wound: The Cold Hearth

This one was the sneakiest. The agents, Glurp learned, kept a kind of warm memory called a **cache**, which made it cheaper to pick up where they left off. But the cache cooled over time. If Glurp stepped away for too long (to make tea, to argue with the goblin, to nap) and then resumed a big, expensive session, the hearth had gone cold, and everything had to be warmed up again at full price.

The worst part was the timing. It always seemed to go cold *just* before they came back.

They called this **the Cold Hearth**: the cache expiring right before an expensive resume.

## Counting the cost

Glurp read the five wounds over by candlelight. None of them was really the tools' fault. The agents were doing what agents do: reading, trying, working hard. The trouble was that nobody was *watching the coins*. Nobody stood at the door counting what went in and what came out, ready to say, "Oi, hang on a minute."

Glurp set down the candle. On the corner of the desk, the crystal ball's inner ring was spinning so fast it hummed.

This time, Glurp noticed.

---

[Previous: The Coming of the Agents](03-the-coming-of-the-agents.md) · [Next: Finding the Meter](05-finding-the-meter.md)
