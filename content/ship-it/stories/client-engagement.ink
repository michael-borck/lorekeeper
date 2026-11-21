VAR client_trust = 50
VAR quality = 50
VAR budget = 50
VAR schedule = 50
VAR accessibility = false
VAR maintainable = false
VAR known_issues = 0
VAR scope_creep = 0

-> start

=== start ===
# IMAGE: assets/images/harbour_hearth_exterior.jpg
# IMAGE_PROMPT: a cosy Perth cafe exterior at morning, warm amber and cream with deep green accents, warm 3D animated feature style, no text
Harbour & Hearth smells of cardamom and strong coffee. Maria meets you at the counter, wiping flour from her hands, already talking. "The paper's running a piece next month — I told them we'd have the site up by then. My nephew made one for the Fremantle shop. Looks fine on his laptop. I want ours, but better. A gallery. A bit of movement."

She slides a laminated menu across the counter. This is the whole engagement, right here, in the first five minutes. How you start sets the tone.

* [Listen to Maria's brief carefully before promising anything]
    You nod, pull out a notebook, and ask her to keep going. You promise nothing about dates yet — you just listen.
    ~ client_trust = client_trust + 5
    ~ quality = quality + 5
    -> maria_brief
* [Reassure Maria you can hit her launch date and get to specifics]
    "We'll make your date," you say, and Maria beams. It feels good. It also just became a promise you haven't costed.
    ~ client_trust = client_trust + 10
    ~ schedule = schedule - 10
    -> maria_brief

=== maria_brief ===
# IMAGE: assets/images/maria_portrait.jpg
# IMAGE_PROMPT: a warm, fast-talking cafe owner in her fifties, apron, expressive face, 1:1 portrait, warm 3D animated feature style, no text
"The budget's a few hundred," Maria says, waving a hand. "Something like the Fremantle one, with the pictures that move." When you ask whether she needs the gallery animation, she nods — but it's the nod of someone who wants the conversation to end.

You know two things she hasn't said: the real budget is smaller, and "a bit of movement" is the most expensive wish on the list. The skill now is separating what she *asks for* from what she *needs*.

* [Ask who will update the site after you leave]
    "Good question," Maria says, surprised anyone asked. "Dev handles all that."
    ~ quality = quality + 5
    -> dev_menu
* [Ask how customers currently find the menu and book]
    "Facebook, mostly. And the phone. We've a PDF menu somewhere." You wince inwardly.
    ~ quality = quality + 5
    -> sam_booking

=== dev_menu ===
# IMAGE: assets/images/dev_spreadsheet.jpg
# IMAGE_PROMPT: an office manager at a cluttered desk with a spreadsheet on screen, slightly wary expression, cosy cafe back-office, warm 3D animated style, no text
Dev runs the roster, the suppliers, the paperwork — and the menu. "Changes every Monday," she says flatly. "Not monthly. Monday." Her spreadsheet is the real source of truth. She's broken WordPress before and doesn't bother hiding it. "Last contractor left nothing. I'm not learning a whole system to change a scone price."

This is the hard constraint hiding under Maria's gallery: a five-minute Monday update, by someone who doesn't trust you to hand over.

* [Note Dev's Monday menu and go talk to a customer]
    You write it down in capitals: MENU EDITABLE IN 5 MINUTES. Dev notices, and softens half a degree.
    ~ client_trust = client_trust + 5
    ~ quality = quality + 5
    -> sam_booking
* [Check the technical inheritance with Alex before scoping]
    "Ask Alex," Dev says. "He knows what mess the old dev left."
    -> alex_warning

=== sam_booking ===
# IMAGE: assets/images/sam_bus.jpg
# IMAGE_PROMPT: a man with low vision using a phone with large text on a bus, screen reader, hurried but calm, warm 3D animated style, no text
You catch Sam outside, a regular, nearby worker, phone in hand. He uses a screen reader and large text. "Tried to book on the bus once," he says. "Couldn't find the button. The menu's a PDF — screen reader just reads 'image, image, image'. I gave up." He shrugs. "I won't try twice. I'll just go to the place up the road."

Accessibility isn't a nice-to-have here. It's the difference between keeping Sam and losing him silently.

* [Call Alex, the IT vendor, about hosting and the old site]
    You thank Sam and dial Alex. He answers on the first ring, already busy.
    ~ quality = quality + 5
    -> alex_warning
* [You've heard enough — write the scope]
    You've got Maria, Dev and Sam. That might be enough — though you never did check the technical inheritance.
    ~ known_issues = known_issues + 1
    -> set_scope

=== alex_warning ===
# IMAGE: assets/images/alex_vendor.jpg
# IMAGE_PROMPT: a blunt, cautious IT vendor in a van, laptop, folded arms, not hostile, warm 3D animated style, no text
Alex is blunt, not hostile. "I've inherited too many dead WordPress sites. Here's what you're walking into: no handover from the last dev, a plugin list a mile long, hosting that may not run current PHP, the domain is in the *previous developer's* name, and the API exposes more than it should." A pause. "I want simple, hard to break, cheap to maintain. And I'm not doing your audit."

He's handed you the real technical map. What you do with it is on you.

* [Pull the requirements together and set the scope]
    You thank Alex. The picture is complete now: Maria, Dev, Sam, and the inheritance.
    ~ quality = quality + 5
    ~ client_trust = client_trust + 5
    -> set_scope

=== set_scope ===
# IMAGE: assets/images/spec_notebook.jpg
# IMAGE_PROMPT: a contractor writing a spec document at a cafe table, coffee, notebook, focused, warm 3D animated style, no text
Four voices, four pulls. Maria's gallery animation. Dev's five-minute Monday update. Sam's booking button above the fold on a phone. Alex's fewer plugins. You can't have all four at full volume. You write `SPEC.md`.

{quality > 65:
You scope tight: an editable menu, accessible booking, minimal plugins. The animation becomes "subtle, if time allows." This locks Act 1 well.
~ maintainable = true
- else:
You scope generously, keeping Maria's animation front and centre and promising to "fit everything in." It reads well. It will cost you later.
~ scope_creep = scope_creep + 1
~ schedule = schedule - 5
}

* [Choose the technology stack]
    SPEC.md saved. Act 2 begins.
    -> stack_choice

=== stack_choice ===
# IMAGE: assets/images/stack_choice.jpg
# IMAGE_PROMPT: a developer at a laptop weighing options, sticky notes labelled with frameworks, warm 3D animated style, no text
The AI assistant is already talking in your editor: "Use React consuming REST — it's the modern choice." It's confident. It's also not the one who'll update the menu on a Monday.

The question isn't what's fashionable. It's what Dev can maintain.

* [Static site — simple, fast, hard to break]
    Clean and quick, but the menu update story needs a backend Dev can touch without you.
    ~ quality = quality + 5
    ~ schedule = schedule + 5
    -> after_stack
* [Classic WordPress theme — Dev knows the admin]
    A content backend Dev can edit in five minutes, few moving parts. Alex nods in your memory.
    ~ maintainable = true
    ~ quality = quality + 10
    -> after_stack
* [React consuming REST — the AI's pick]
    Slick. Impressive in a viva. Also the thing Dev will fear on a Monday and the thing Alex warned against.
    ~ scope_creep = scope_creep + 1
    ~ budget = budget - 10
    ~ schedule = schedule - 10
    ~ maintainable = false
    -> after_stack

= after_stack
You justify the choice in `DECISIONS.md` — against the client's capacity, not the AI's enthusiasm.
-> lighthouse_fail

=== lighthouse_fail ===
# IMAGE: assets/images/lighthouse_audit.jpg
# IMAGE_PROMPT: a browser audit report showing red warnings, contrast and performance meters, warm 3D animated style, no text
You build the first pages and run an audit. Red flags: the brand's amber-on-cream fails contrast, and the mobile load is slow. Sam is standing invisibly behind every one of these numbers.

* [Fix the contrast and performance now]
    You adjust the palette within brand tolerance and trim the mobile payload. Sam can read it.
    ~ accessibility = true
    ~ quality = quality + 10
    ~ schedule = schedule - 5
    -> plugin_security
* [Defer it — note it and move on]
    You log it as a known issue. A promise to future-you.
    ~ known_issues = known_issues + 1
    -> plugin_security
* [Ignore it — the colours are the brand]
    You tell yourself the brand is the brand. Sam disagrees, silently.
    ~ accessibility = false
    ~ known_issues = known_issues + 1
    ~ quality = quality - 5
    -> plugin_security

=== plugin_security ===
# IMAGE: assets/images/plugin_warning.jpg
# IMAGE_PROMPT: a screen showing a plugin with a security warning badge, warm 3D animated style, no text
Configuring the backend, you find a plugin that does what you want — and carries a known security issue, plus a load of bloat. Alex's voice: *fewer plugins.*

* [Remove it and build the feature by hand]
    Leaner, safer, yours to maintain. A little slower to build.
    ~ quality = quality + 5
    ~ schedule = schedule - 5
    -> booking_endpoint
* [Patch it and keep it updated]
    A reasonable middle path — if someone keeps updating it. That someone is Dev.
    ~ known_issues = known_issues + 1
    -> booking_endpoint
* [Accept the risk — it works today]
    It works today. Alex's warning echoes anyway.
    ~ known_issues = known_issues + 2
    ~ quality = quality - 5
    -> booking_endpoint

=== booking_endpoint ===
# IMAGE: assets/images/booking_endpoint.jpg
# IMAGE_PROMPT: a developer reviewing a REST API data contract, booking form on a phone, warm 3D animated style, no text
The booking REST endpoint is misconfigured — exposing more than it should, exactly as Alex predicted — and confirmation emails aren't reaching users. Sam needs to *know* the booking worked, or he's gone.

* [Fix the data contract and confirmations properly]
    You lock the endpoint down and get confirmations landing. Sam would get his "you're booked."
    ~ quality = quality + 10
    ~ schedule = schedule - 5
    -> ai_code
* [Ship the fragile flow — it mostly works]
    It books, sometimes silently. Sam won't trust silence, and he won't complain twice.
    ~ known_issues = known_issues + 2
    ~ quality = quality - 10
    -> ai_code

=== ai_code ===
# IMAGE: assets/images/ai_assistant.jpg
# IMAGE_PROMPT: a glowing AI code suggestion on screen, a contractor looking uncertain, warm 3D animated style, no text
The AI writes a slick feature in seconds. It works. You don't fully understand it — and your viva asks you to explain every line, while Dev has to live with it.

* [Strip it back to something you can maintain and hand over]
    You rewrite it simply. Less dazzling, fully yours, handover-ready.
    ~ maintainable = true
    ~ quality = quality + 5
    ~ schedule = schedule - 5
    -> one_more_feature
* [Spend time learning it line by line]
    You invest hours. You can now explain it — but the clock moved.
    ~ quality = quality + 5
    ~ schedule = schedule - 10
    -> one_more_feature
* [Keep it as-is — it works, ship it]
    Code you can't explain, in a site someone else must maintain. A quiet debt.
    ~ known_issues = known_issues + 1
    ~ maintainable = false
    -> one_more_feature

=== one_more_feature ===
# IMAGE: assets/images/one_more_feature.jpg
# IMAGE_PROMPT: a cafe owner showing a phone with an animation idea, a contractor weighing the clock, warm 3D animated style, no text
Late in the build, Maria calls. "Could we add the moving gallery after all? The Fremantle one has it." The budget and clock are already tight.

* [Hold the line — it's out of scope]
    "Not this round," you say gently, pointing at SPEC.md. Maria grumbles but respects it.
    ~ client_trust = client_trust - 5
    ~ quality = quality + 5
    -> launch_pressure
* [Negotiate a trade — swap it for something]
    You offer a simple, accessible image strip instead of a heavy animation. Maria agrees.
    ~ client_trust = client_trust + 5
    ~ quality = quality + 5
    ~ schedule = schedule - 5
    -> launch_pressure
* [Accept it against the clock and budget]
    You say yes. The gallery goes in. So does the overrun.
    ~ scope_creep = scope_creep + 1
    ~ budget = budget - 10
    ~ schedule = schedule - 10
    ~ client_trust = client_trust + 5
    -> launch_pressure

=== launch_pressure ===
# IMAGE: assets/images/launch_pressure.jpg
# IMAGE_PROMPT: a cafe owner eager to launch, a paper journalist waiting, a nervous developer, warm 3D animated style, no text
Act 3. "The paper's ready," Maria says. "Can we go live before the audit?" She never did tell Dev the date. {accessibility == false: The brand colours still fail contrast. } {known_issues > 2: Several known issues remain on the register. }

What ships, and what cannot?

* [Ship only what's ready; finish the rest first]
    You hold launch until the booking flow and accessibility clear. Maria frets, then trusts you.
    ~ quality = quality + 10
    ~ schedule = schedule - 5
    ~ client_trust = client_trust - 5
    -> final_recommendation
* [Launch now, fix the rest after]
    You go live for the paper and promise to patch. The register comes with you.
    ~ client_trust = client_trust + 5
    ~ known_issues = known_issues + 1
    -> final_recommendation

=== final_recommendation ===
# IMAGE: assets/images/audit_memo.jpg
# IMAGE_PROMPT: a board meeting with a non-technical client, an audit memo, plain-language explanation, warm 3D animated style, no text
Two years on. The board weighs a WordPress agency against an AI site-builder subscription. You deliver the audit memo and explain your recommendation in plain language — no jargon, just what it means for Dev's Mondays and Sam's bookings.

Your record speaks now.

* {client_trust >= 65 and accessibility and maintainable and known_issues <= 1} [Recommend the honest, simple path]
    -> ending_trusted
* {accessibility and maintainable and client_trust < 65} [Deliver on constraints despite friction]
    -> ending_accessible
* {known_issues >= 3 and client_trust >= 40} [Ship it anyway]
    -> ending_fragile
* {budget <= 25 or schedule <= 15 or scope_creep >= 3} [Deliver the ambitious build]
    -> ending_overengineered
* {client_trust < 40} [Watch Maria take the AI subscription]
    -> ending_client_walks
* [Ship the modest site that works]
    -> ending_quiet

=== ending_trusted ===
# IMAGE: assets/images/ending_trusted.jpg
# IMAGE_PROMPT: a celebratory cafe launch, accessible site on a phone, happy owner and staff, 4:5 ending card, warm 3D animated style, no text
A trusted, accessible, maintainable launch, on a realistic schedule. Dev updates the menu in minutes. Sam books in under a minute and gets his confirmation. The board keeps the agency relationship over the AI subscription — because the humans listened.

**Debrief.** You listened least to the AI's fashion; good. With another week you'd polish the gallery you kept modest. The first issue you'd fix after launch: the plugin update cadence, so Dev never has to think about it.
# ENDING: good
-> END

=== ending_accessible ===
# IMAGE: assets/images/ending_accessible.jpg
# IMAGE_PROMPT: a solid working site, slightly tense owner, a maintainable backend, 4:5 ending card, warm 3D animated style, no text
Accessibility and maintainability: met. Sam can book; Dev can edit. But missed dates bruised Maria's trust. A solid professional outcome, if a slightly cooler handshake.

**Debrief.** You listened least to Maria's deadline anxiety. With another week you'd have communicated schedule earlier. First fix after launch: a status page so Maria never feels in the dark again.
# ENDING: good
-> END

=== ending_quiet ===
# IMAGE: assets/images/ending_quiet.jpg
# IMAGE_PROMPT: an unremarkable but working cafe website, nobody noticing, quiet satisfaction, 4:5 ending card, warm 3D animated style, no text
An unremarkable site that just works. Nobody writes a review about it. Dev updates it in five minutes. Sam books in under a minute. Modest, and real.

**Debrief.** You listened least to ambition — no harm done. With another week you'd add the subtle polish Maria wanted. First fix after launch: tighten the booking confirmation copy.
# ENDING: neutral
-> END

=== ending_fragile ===
# IMAGE: assets/images/ending_fragile.jpg
# IMAGE_PROMPT: a launched site with hidden cracks, a worried office manager eyeing Monday, 4:5 ending card, warm 3D animated style, no text
You hit the date — and shipped known issues and a brittle booking flow. Sam tries once, hits silence, and goes up the road. Dev dreads every Monday.

**Debrief.** You listened least to Sam. With another week you'd have fixed the confirmations before launch. First fix after launch: the booking data contract, before more customers vanish quietly.
# ENDING: bad
-> END

=== ending_overengineered ===
# IMAGE: assets/images/ending_overengineered.jpg
# IMAGE_PROMPT: an impressive but broken fancy site, over budget, a baffled office manager, 4:5 ending card, warm 3D animated style, no text
You chased React, plugins and animation. It's impressive. It's over budget, over schedule, and Dev can't touch it without calling you. Impressive and unusable.

**Debrief.** You listened least to Dev's five-minute Monday. With another week you'd have simplified the stack — but time was the thing you spent. First fix after launch: strip the stack back to something maintainable.
# ENDING: bad
-> END

=== ending_client_walks ===
# IMAGE: assets/images/ending_client_walks.jpg
# IMAGE_PROMPT: an empty cafe table, a contract uncompleted, an owner choosing an app, 4:5 ending card, warm 3D animated style, no text
Trust collapsed. Promises broke, the launch slipped, the paper piece ran without a working site. Maria signs up for the AI subscription and thanks you politely. You've lost the client.

**Debrief.** You listened least to Maria — her deadline, her budget, her need to not feel managed. With another week you'd have rebuilt trust with honest updates. First fix: nothing technical. The relationship was the system that failed.
# ENDING: bad
-> END