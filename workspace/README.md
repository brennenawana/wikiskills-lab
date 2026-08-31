# workspace/ — your private data

Everything the coach generates **for you** lands in this folder, and only here.
Git ignores all of it (this README is the one exception). Nothing in this
folder is ever committed, uploaded, or shared. Delete the folder and every
trace of your engagement is gone.

What lands here as the steps run:

| Folder | Contents | Written during |
|---|---|---|
| `profile/` | Your interview answers, the map of your repos and services, and `state.json` (where you are in the process) | Step 1 |
| `ledgers/` | Records of your observed work sessions: what was read, called, and spent | Step 2 |
| `capsules/` | Frozen copies of observed tasks, so tests stay repeatable while your real work moves on | Step 2 |
| `suite/` | Your measuring stick: the metric, the test tasks, the scorers, your baseline score | Step 4 |
| `contract/` | The budgets, run counts, and stop rules you approved | Step 4 |
| `wiki/` | The knowledge the improvement loop builds up | Step 5 |
| `skills/` | Accepted improvements, ready to install into your daily work | Step 5 |
| `runs/` | Spend ledgers, run outputs, and results | Steps 4–5 |

One safety rule the coach follows everywhere: secret values (tokens, keys,
passwords) are never written into these files — only the fact that one exists.
