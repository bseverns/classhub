# Somali Localization Review Packet

Purpose: support human Somali-language review on trust-critical family-facing copy.

Review focus:
- Join flow
- Privacy summary
- My Data
- Portfolio
- Invite/join warnings
- Return-code and shared-device language

How to use:
1. Review each "Current Somali" string for clarity, tone, and classroom trust.
2. Update `services/classhub/locale/so/LC_MESSAGES/django.po`.
3. Recompile with `msgfmt -o services/classhub/locale/so/LC_MESSAGES/django.mo services/classhub/locale/so/LC_MESSAGES/django.po`.
4. Run `python3 scripts/check_i18n_spanish_somali_parity.py`.

Status key:
- `Translated`: Somali copy differs from English source.
- `Fallback (English)`: still identical to English and should be reviewed first.

| Area | English source | Current Somali | Status |
|---|---|---|---|
| Join flow | Join your class | Ku biir fasalkaaga | Translated |
| Join flow | Enter your class code and pick a display name. | Geli koodhka fasalkaaga oo dooro magac muuqda. | Translated |
| Join flow | Enter the class code from your teacher. Pick any display name you like. | Geli koodhka fasalka ee macallinkaaga. Dooro magac muuqda oo aad jeceshahay. | Translated |
| Join flow | On shared devices, enter your return code so you do not join as another student. | Qalabka la wadaago, geli koodhkaaga soo laabashada si aadan ugu biirin adigoo ah arday kale. | Translated |
| Join flow | Same classroom device? You can usually leave return code blank. | Isla qalabkii fasalka? Badanaa waxaad ka tagi kartaa koodhka soo laabashada oo bannaan. | Translated |
| Join flow | On shared devices, use your own return code to avoid signing in as someone else. | Qalabka la wadaago, isticmaal koodhkaaga soo laabashada si aadan ugu gelin qof kale. | Translated |
| Join flow | A nickname or made-up name is fine - no need to use your real name. | Magac naanays ah ama magac la sameeyay waa hagaag - looma baahna inaad isticmaasho magacaaga dhabta ah. | Translated |
| Join flow | Return code (optional) | Koodhka soo laabashada (ikhtiyaari) | Translated |
| Join flow | If your class uses icon codes, use the icon keypad below. | Haddii fasalkaagu isticmaalo koodhadh astaamo ah, isticmaal keypad-ka astaamaha ee hoose. | Translated |
| Join flow | Show icon keypad | Muuji keypad-ka astaamaha | Translated |
| Join flow | Clear return code | Nadiifi koodhka soo laabashada | Translated |
| Join flow | Return code icon keypad | Keypad-ka astaamaha koodhka soo laabashada | Translated |
| Privacy summary | Privacy at a glance: | Dulmar Asturnaanta: | Translated |
| Privacy summary | We store your display name, class submissions, and event timestamps. | Waxaan kaydinnaa magacaaga muuqda, gudbinnada fasalka, iyo waqtiyada dhacdooyinka. | Translated |
| Privacy summary | Storage location: | Goobta kaydinta: | Translated |
| Privacy summary | Retention: | Retention: | Fallback (English) |
| Privacy summary | day(s). Deleted sooner on request. | day(s). Deleted sooner on request. | Fallback (English) |
| Privacy summary | submissions stay until a teacher or admin removes them. | submissions stay until a teacher or admin removes them. | Fallback (English) |
| Privacy summary | Delete now: | Hadda tirtir: | Translated |
| Privacy summary | delete your work or end session. | tirtir shaqadaada ama dhammee fadhiga. | Translated |
| Privacy summary | No tracking. No ads. No data broker sharing. | Ma jiro raadraac. Ma jiro xayeysiis. Lama wadaago dilaaliinta xogta. | Translated |
| My Data | My Data | Xogtayda | Translated |
| My Data | Stored data: your display name, submissions, and class event timestamps. | Xogta la kaydiyo: magacaaga muuqda, gudbinnada, iyo waqtiyada dhacdooyinka fasalka. | Translated |
| My Data | Storage location: this server is hosted locally by your school or organization. | Goobta kaydinta: server-kan waxaa deegaanka ku martigelisa dugsigaaga ama ururkaaga. | Translated |
| My Data | Delete all of your submissions now? | Ma tirtirtaa hadda dhammaan gudbinnadaada? | Translated |
| My Data | Delete my work now | Hadda tirtir shaqadayda | Translated |
| My Data | End my session on this device | Ku dhammee fadhigayga qalabkan | Translated |
| Portfolio | Filters | Shaandheeyayaal | Translated |
| Invite warnings | That invite link is not valid. | Xiriirka casuumaaddan sax ma aha. | Translated |
| Invite warnings | That invite link has been disabled. | Xiriirka casuumaaddan waa la naafo gareeyay. | Translated |
| Invite warnings | That invite link has expired. | Xiriirka casuumaaddan wuu dhacay. | Translated |
| Invite warnings | This invite is full right now. Ask your teacher for a new invite link. | Casuumaaddan hadda way buuxdaa. Weydii macallinkaaga xiriir casuumaad cusub. | Translated |
| Invite warnings | That invite link is not usable right now. | Xiriirka casuumaaddan hadda lama isticmaali karo. | Translated |
| Invite warnings | That looks like an email address. Please use a nickname or display name instead. | Taasi waxay u egtahay cinwaan iimayl. Fadlan isticmaal naanays ama magac muuqda. | Translated |
| Invite warnings | That looks like a phone number. Please use a nickname or display name instead. | Taasi waxay u egtahay lambar telefoon. Fadlan isticmaal naanays ama magac muuqda. | Translated |
| Invite warnings | Please use a nickname or display name instead of personal information. | Fadlan isticmaal naanays ama magac muuqda halkii aad ka isticmaali lahayd xog shakhsiyeed. | Translated |
| Invite warnings | Heads-up: that looks like an email address. A nickname is safer. | Ogeysiis: taasi waxay u egtahay cinwaan iimayl. Naanays ayaa ka ammaan badan. | Translated |
| Invite warnings | Heads-up: that looks like a phone number. A nickname is safer. | Ogeysiis: taasi waxay u egtahay lambar telefoon. Naanays ayaa ka ammaan badan. | Translated |
| Invite warnings | Consider using a nickname instead of personal information. | Ka fiirso inaad isticmaasho naanays halkii xog shakhsiyeed. | Translated |
