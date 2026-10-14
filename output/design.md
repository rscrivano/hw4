# Campus Customs: Interactive Design (Problem 10)

Problem 9 made the shop *work*: a cart, guest checkout, recommendations and restocking. Problem 10 makes it *fun to use*. The three changes below are small, playful moments built around our mascot, **Handsome Dan**. Their job is to **keep shoppers engaged on the site** so they stay longer, browse more items, and feel good about adding (and keeping) things in their cart instead of leaving the page.

| # | Interaction | When it happens | Feeling we want |
|---|---|---|---|
| 1 | **Handsome Dan barks** ("woof-woof!") and his logo wiggles | Clicking the Handsome Dan logo to go back to the home page | Delight, brand personality, "this store is alive" |
| 2 | **Fly-to-cart bubble:** the product photo in a round bubble arcs into the cart icon, which then hops | Clicking **Add to cart** on a product page | Satisfaction, "it's in my cart!" |
| 3 | **Handsome Dan growls** | Clicking **Remove** on an item in the Cart | A playful nudge: "are you sure?" |
| + | **🔊/🔇 sound toggle** | Always in the nav bar | Shopper control. Nobody gets stuck with sounds they don't want |

Code: `frontend/src/fx.ts` (all sounds and the bubble animation), wired into `components/NavBar.tsx` (bark, wiggle, sound toggle), `pages/ProductDetail.tsx` (fly-to-cart) and `pages/Cart.tsx` (growl). Styles are in `styles.css` under "interactive effects (Problem 10)".

---

## 1. Handsome Dan barks on the way home

### What changed
- The Handsome Dan logo in the top-left already linked to the home page. Now clicking it also plays a short, friendly **"woof-woof!"**: two quick barks, the second slightly higher.
- At the same time, the little Dan face does a **head-wiggle** (a quick tilt left and right).
- The bark is **generated in the browser** with the Web Audio API, by shaping a falling tone and a breathy burst into a bark. There's no audio file, so nothing to license or download, and it doesn't slow the page down.

### Why it keeps shoppers engaged
- **It turns navigation into a reward.** "Go home" is usually a dead click. Hearing Dan bark makes it a tiny moment of fun that encourages shoppers to keep clicking around and exploring.
- **It builds personality and brand memory.** Handsome Dan is Yale's beloved mascot. A store that *barks back* is memorable and shareable, and students and alumni are more likely to come back to a site that feels like Yale.
- **It's a "surprise and delight" detail.** Small unexpected touches make a site feel crafted and trustworthy, and that makes people more comfortable buying.

---

## 2. The fly-to-cart bubble

### What changed
- When a shopper clicks **Add to cart**, a **round bubble containing the product's photo** (white border, pink glow) appears:
  - It pops up at the product photo, or at the button if the photo has scrolled out of view.
  - It **arcs up and across the screen** and shrinks into the 🛒 **cart icon**, in about 0.85 seconds.
- When it lands, the **cart icon hops** and the **count badge goes up**.
- It always flies to the cart icon you can actually see: the desktop nav link, or the phone cart button.

### Why it keeps shoppers engaged
- **Instant, visible confirmation.** The shopper *sees* the exact item go into the cart, so there's no doubt the click worked. That removes the "did it add?" worry that makes people click twice or give up.
- **It teaches where the cart is.** The animation draws the eye straight to the cart icon, so shoppers know exactly where to go to review and check out. That makes the path to purchase obvious.
- **It makes adding to cart satisfying.** A rewarding animation makes people more willing to add a second or third item, which means bigger baskets.
- **It keeps them on the page.** The bubble flies to the cart instead of taking the shopper to the cart page, so they **stay on the product** and can keep browsing the "You might also like" picks underneath.

---

## 3. Handsome Dan growls when you remove something

### What changed
- On the Cart page, clicking **Remove** now plays a low, rumbling **dog growl** (about 1 second) as the item is removed.
- Like the bark, it's generated in the browser: a low, wobbling tone with a rough rumble and throaty noise. No sound file is needed.

### Why it keeps shoppers engaged
- **A playful "are you sure?".** Without blocking the shopper or adding an annoying confirmation pop-up, the growl hints that Dan would rather they kept it. That makes shoppers pause and reconsider before removing items, which helps keep more items in carts.
- **Consistent personality.** Dan is happy when you come home (bark) and grumpy when you take things out of your cart (growl). That emotional consistency makes the mascot feel like a real shopping companion, the same Dan who chats with them.
- **It never gets in the way.** The item is still removed immediately. The growl is feedback, not a barrier, so shoppers stay in control and don't feel trapped.

---

## Respecting the shopper (the guard-rails)

Engagement features only work if they never annoy or exclude anyone:
- **🔊/🔇 sound toggle in the nav bar.** One click mutes every sound on the site. The choice is remembered on that browser (`localStorage`). Testing confirmed that, when muted, clicking the logo still goes home but plays **no** sound.
- **Sounds only play right after a click.** Nothing plays on page load or while scrolling, and browsers block sound without a click anyway.
- **Reduced motion is respected.** If a shopper's device is set to "reduce motion", the bubble flight and the wiggle are skipped and the cart simply updates. The sounds still play, unless muted.
  - The browser pane used for testing had reduced motion turned on, and the site correctly skipped the animations there. The animation tests below simulated the normal setting.
- **Screen readers aren't affected.** The bubble is decorative (`aria-hidden`), and the sound button has clear labels ("Mute site sounds" / "Turn site sounds on") and `aria-pressed`.
- **Nothing extra is downloaded.** The sounds are generated in code and the bubble reuses the product photo that's already loaded.

---

## How it was verified

In the browser pane at phone width (screenshots in `output/screenshots/p10_*`):

| Check | Result |
|---|---|
| Bark and growl are real, distinct sounds: rendered offline with `OfflineAudioContext` and measured | **Bark:** 2 separate bursts, ~360 Hz, about 0.21 s of audible sound. **Growl:** 1 sustained burst, low ~100 Hz, about 0.6 s at full volume |
| Clicking the Handsome Dan logo on `/products` | Went to `/`. **2** sound voices started (the two woofs), and the logo got the `wiggle` animation |
| Add to cart on the Crew Left Chest Hoodie (XS) | The bubble with `crew-left-chest-hoodie.jpg` was tracked over **52 frames**: it started at the button, rose to the top of the screen at the halfway point, ended **exactly** on the cart icon centre and shrank 84 px → 15 px. Then it was removed, and the badge went **0 → 1**, then **2** on the second add |
| Freeze-frame of the bubble mid-flight | `p10_fly_to_cart_bubble.jpg` shows the round hoodie bubble with its pink ring flying into the cart icon |
| Remove on the Cart page | The growl started (sawtooth voice + 22 Hz "rrr" wobble + 17 Hz rumble). The item was removed and the cart showed "Your cart is empty" |
| 🔇 mute, then click the logo | The setting was saved as `off`. Navigation still worked, and **0** sounds started |
| Layout | Adding the 🔊 button made the phone nav **too wide** (399px in 350px), which pushed the ☰ menu off-screen. Fixed with tighter spacing on small phones, and re-measured at 350px in 350px |
| Production build and console | The build passes. Fresh page loads have no errors |

**Before and after:** before, adding to the cart only showed a text message, removing was silent, and the logo was a plain link. After, each of these key moments has a matching sight or sound. The bark and the growl give Handsome Dan a personality, and the bubble gives clear visual feedback, all aimed at keeping shoppers browsing, adding and buying.
