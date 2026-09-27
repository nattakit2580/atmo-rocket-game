# Permission request — template

Send to: **api@letterboxd.com** (and/or Letterboxd support via <https://letterboxd.com/contact/>)
Put the project title in the subject line, as Letterboxd's API page requests.

---

**Subject:** Academic research data request — "[THESIS TITLE]" ([UNIVERSITY])

Dear Letterboxd team,

My name is [NAME], and I am a [degree] student at [UNIVERSITY], supervised by [SUPERVISOR, e-mail]. My thesis, "[THESIS TITLE]", analyses the language of English-language film reviews.

I am writing to ask for permission to use Letterboxd review data for this non-commercial academic research. I have read your Terms of Use and understand that automated scraping is not permitted, so I have not collected any data and will not do so without your authorisation.

**Scope requested**
- Films: 40 titles (list attached)
- Per film: the text, date and star rating of public reviews, from which I will draw a random sample of 500 English reviews
- Total used in the analysis: about 20,000 reviews
- Access method: any method you prefer, e.g. API access limited to the review endpoints for these films, a data extract provided by you, or permission to record reviews manually at a low rate

**Safeguards**
- Used only for this thesis; no commercial use, no redistribution of the full texts, and no training of generative AI models
- Usernames are replaced by one-way pseudonymous IDs; no profile data is collected
- Results are reported in aggregate, with only short, unattributed quotations
- Data will be stored securely and deleted on [DATE] or when you ask
- Letterboxd will be credited as the data source in the thesis

I am happy to follow any conditions you set and to share the finished thesis with you.

Thank you for considering this request.

Kind regards,
[NAME]
[UNIVERSITY / DEPARTMENT]
[E-MAIL]

---

Keep the reply. Record its date and reference in `config/data_source.json` → `permission_reference`.
