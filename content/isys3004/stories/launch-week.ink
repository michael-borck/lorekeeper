VAR quality = 0
VAR trust = 0
VAR accessible = 0

-> start

=== start ===
It is Wednesday. The launch is Friday. Maria has sent three messages, Dev has sent one, and Sam has not sent any because he gave up on the booking form last week.

Maria wants the gallery animation. Dev wants the menu update to take five minutes. Sam needs the booking action to work on a phone.

* [Protect the booking path and defer the animation]
    ~ quality = quality + 2
    ~ trust = trust + 1
    You write the decision down: booking first, animation only if time allows. Maria is disappointed for one message, then agrees to see the booking flow.
    -> test
* [Add the animation because Maria asked for it]
    ~ quality = quality - 1
    ~ trust = trust + 1
    The gallery moves. It looks impressive on your laptop. You have not tested the booking form on a phone yet.
    -> test
* [Ask Maria for a one-week delay]
    ~ trust = trust + 2
    ~ quality = quality + 1
    You explain what is still unsafe. Maria does not love it, but she would rather launch once than apologise twice.
    -> test

=== test ===
The booking form is the one task every customer will try. The animation is the one nobody needs. The menu is the one Dev will change every Monday.

* [Test the three top tasks on a phone and with a keyboard]
    ~ quality = quality + 2
    ~ accessible = accessible + 2
    You book on a 375px screen, tab to the button, submit, and read the confirmation with a screen reader. Two small issues appear; both are fixable tonight.
    -> decide
* [Test the happy path in your browser]
    ~ quality = quality - 1
    The desktop happy path works. The phone is still an assumption.
    -> decide
* [Ship now and watch the analytics]
    ~ quality = quality - 1
    ~ trust = trust - 1
    You ship. The dashboard is quiet. The support inbox is not.
    -> decide

=== decide ===
The site is ready enough to make a decision. The question is what the client is actually buying.

* [Write the known issues and launch]
    -> ending
* [Delay the launch and fix the booking path]
    ~ quality = quality + 2
    ~ trust = trust + 1
    You call Maria, explain the one remaining risk, and move the launch by two days. She agrees when she sees the booking flow working.
    -> ending

=== ending ===
{quality >= 4 and accessible >= 2:
    -> ending_solid
- else:
    {trust >= 3:
        -> ending_delayed
    - else:
        -> ending_fragile
    }
}

=== ending_solid ===
# ENDING: A quiet, solid launch
The site launches. Nobody writes a dramatic review, because nothing breaks. Sam books a table on the bus. Dev changes the menu on Monday without calling you.

That is the last 20 percent: not more features, fewer surprises.

-> END

=== ending_delayed ===
# ENDING: A brave delay
You move the date. The client is not thrilled, but the booking path works and the animation is documented as a later improvement.

The launch is smaller and calmer than the promise. It also survives the first week.

-> END

=== ending_fragile ===
# ENDING: It looked fine on the laptop
The launch goes ahead. On a phone, the booking button sits off-screen. Sam tries once, then goes to the cafe up the road.

The analytics say the site is live. The customer says otherwise.

-> END
