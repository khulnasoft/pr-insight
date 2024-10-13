# Overview - Impact Evaluation 💎

Demonstrating the return on investment (ROI) of AI-powered initiatives is crucial for modern organizations.
To address this need, PR-Insight has developed an AI impact measurement tools and metrics, providing advanced analytics to help businesses quantify the tangible benefits of AI adoption in their PR review process.


## Auto Impact Validator - Real-Time Tracking of Implemented PR-Insight Suggestions

### How It Works
When a user pushes a new commit to the pull request, PR-Insight automatically compares the updated code against the previous suggestions, marking them as implemented if the changes address these recommendations, whether directly or indirectly:

1. **Direct Implementation:** The user directly addresses the suggestion as-is in the PR, either by clicking on the "apply code suggestion" checkbox or by making the changes manually.
2. **Indirect Implementation:** PR-Insight recognizes when a suggestion's intent is fulfilled, even if the exact code changes differ from the original recommendation. It marks these suggestions as implemented, acknowledging that users may achieve the same goal through alternative solutions.

### Real-Time Visual Feedback
Upon confirming that a suggestion was implemented, PR-Insight automatically adds a ✅ (check mark) to the relevant suggestion, enabling transparent tracking of PR-Insight's impact analysis.
PR-Insight will also add, inside the relevant suggestions, an explanation of how the new code was impacted by each suggestion.

![Suggestion_checkmark](https://khulnasoft.com/images/pr_insight/auto_suggestion_checkmark.png){width=512}

### Dashboard Metrics
The dashboard provides macro-level insights into the overall impact of PR-Insight on the pull-request process with key productivity metrics.

By offering clear, data-driven evidence of PR-Insight's impact, it empowers leadership teams to make informed decisions about the tool's effectiveness and ROI.

Here are key metrics that the dashboard tracks:

#### PR-Insight Impacts per 1K Lines
![Dashboard](https://khulnasoft.com/images/pr_insight/impacts_per_1k_llines.png){width=512}
> Explanation: for every 1K lines of code (additions/edits), PR-Insight had on average ~X suggestions implemented.

**Why This Metric Matters:**

1. **Standardized and Comparable Measurement:** By measuring impacts per 1K lines of code additions, you create a standardized metric that can be compared across different projects, teams, customers, and time periods. This standardization is crucial for meaningful analysis, benchmarking, and identifying where PR-Insight is most effective.
2. **Accounts for PR Variability and Incentivizes Quality:** This metric addresses the fact that "Not all PRs are created equal." By normalizing against lines of code rather than PR count, you account for the variability in PR sizes and focus on the quality and impact of suggestions rather than just the number of PRs affected.
3. **Quantifies Value and ROI:** The metric directly correlates with the value PR-Insight is providing, showing how frequently it offers improvements relative to the amount of new code being written. This provides a clear, quantifiable way to demonstrate PR-Insight's return on investment to stakeholders.

#### Suggestion Effectiveness Across Categories
![Impacted_Suggestion_Score](https://khulnasoft.com/images/pr_insight/impact_by_category.png){width=512}
> Explanation: This chart illustrates the distribution of implemented suggestions across different categories, enabling teams to better understand PR-Insight's impact on various aspects of code quality and development practices.

#### Suggestion Score Distribution
![Impacted_Suggestion_Score](https://khulnasoft.com/images/pr_insight/impacted_score_dist.png){width=512}
> Explanation: The distribution of the suggestion score for the implemented suggestions, ensuring that higher-scored suggestions truly represent more significant improvements. 