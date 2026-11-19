CST4225 – Coursework 1 (30%)
Title: Airbnb Rental Income & Listing Success Prediction
Platform: Dataiku (Python if needed)
Deadline: 6
th December 2026
Submission: Upload to MyLearning → Link will be shared
Word Limit: 2000 words (Main Questions -excluding code, tables, figures etc)


Overview
In this challenge, you will 
        build: a predictive model to estimate the success of Airbnb property listings. 
                Success: Represented by a categorical variable (e.g., Good / Bad listing) — 
                            derived using own formula based on key indicators such as price,occupancy, and reviews.

Work through the full data science lifecycle for this objective: 
domain familiarisation, 

feature engineering, 

model development, 

evaluation, and 

interpretation

— while maintaining proper documentation and a reproducible workflow in Dataiku.
Python may be used where needed.

In addition, you should propose: 
        one additional data science use case that could be developed using the Airbnb datasets. 
        For this second objective:

                Required to explain what the proposed use case is, 
                                    why it is useful, 
                                    what data would be required,
                                    and how it could potentially be developed. 
                                    (You are not required to execute the full lifecycle for Objective 2.)


The provided dataset contains a wide range of attributes related to Airbnb listings, 
        such as property type, 
                location, 
                number of bedrooms, 
                amenities, 
                rental price, and more.

Additionally, a second dataset provides information on Airbnb
        customer reviews, which could be used as a proxy to measure how many tourists rent each Airbnb listing. 

Finally,a third dataset provides information on 
        the different neighbourhoods of London.
The dataset is uploaded on MyLearning, and can also be downloaded from:
http://insideairbnb.com/get-the-data

Overall Guidelines
1. Build Domain Knowledge & Frame the Problem: 
    Begin by understanding the context and dynamics of the Airbnb marketplace. 
    Strengthen your domain knowledge using available datasets and reliable sources to 
    identify what defines success in property listings. 
    Use this understanding to guide your data exploration and modeling direction throughout the challenge.

2. Define & Construct the Success Metric: 
    Establish a clear and measurable indicator of success based on data-driven logic (Good/Bad listing). 
    The dependent variable should capture listing performance meaningfully and 
    be justified using available attributes. 
    (Ensure your success metric aligns with business understanding and can be reproduced consistently)
    .
3. Data Pre-processing & Feature Engineering: 
    Clean and prepare your data systematically to improve model quality. 
    Apply relevant transformations, 
    handle missing values, and 
    create features that enhance prediction capability. 
    Each preprocessing decision should be purposeful and rooted in analytical reasoning.

4. Model Building & Evaluation: 
    Develop and refine your predictive model using sound analytical methods. 
    Experiment with suitable algorithms, 
    adjust variables, and 
    validate model performance using appropriate evaluation metrics. 
    goal is to achieve a balance between accuracy, 
                                        interpretability, and
                                        generalisability (your Dataiku workflow and/or Python code should reflect this).

5. Model Interpretation & Business Translation: 
    Focus on interpreting your model outcomes to generate actionable insights. 
    Identify the most influential variables and 
    explain their significance in business terms. 
    Emphasize clarity and practical relevance over purely statistical descriptions.

6. Critical Reflection & Product Development: 
    Evaluate the overall process critically, 
    highlighting what worked well and what could be improved. 
    Discuss potential scalability, automation, or productisation of your solution. 
    Reflecting on limitations and future opportunities demonstrates applied understanding and innovation.

7. Propose an Additional Data Science Use Case: 
    Identify one additional Airbnb related business or analytical problem that could be addressed using the available datasets or suitable additional data. 
    Explain what the use case is, 
    who would benefit from it, 
    what data would be required, and 
    how it could potentially be approached using data science.

Template for Report Preparation
Important:
The entire report must be written in this pattern.

For each question, 
    all written explanations and interpretations appear first,
    followed by all Dataiku screenshots, Python code segments, model outputs, charts, or other technical evidence at the end.

    Technical evidence must be clearly referenced in the report text as Q1A, Q1B, etc.
Example:
To explore the distribution of property types across the dataset, I created a bar chart
illustrating the most common Airbnb property categories (see Q1A visual). The resulting
visualization highlights that entire apartments and private rooms make up over 80% of
listings (see Q1B Dataiku output).
Where Python is used, relevant code should also be placed at the end of the respective
question.

Q1. Domain Knowledge Building (1 paragraph)
    What process did you follow to understand Airbnb’s business model, 
    host success metrics, or pricing factors?
    1-2 para max
Suggested Dataiku evidence:
If you performed any initial profiling, charts, distributions, or exploratory analysis in
Dataiku, include relevant screenshots at the end as Q1A, Q1B, etc.

Q2. Data Sourcing
    Did you use any additional dataset beyond the given one? (Yes/No)
    If Yes, describe:
    • What data you sourced (2–3 lines)
    • The exact reference or link(s)
    • How you merged the data (3 bullet points: join keys, merge method, checks)
    If possible, give a screenshot of how merged data looks like (or data structure)

Q3. Dependent Variable Formulation
    (a) Describe your formula for defining Good/Bad listing (e.g., based on revenue, rating,
    occupancy). Explain the logic in one paragraph.
    (b) Show the formula used to generate this dependent variable.
    This can be created using:
    • Dataiku formula
    • Prepare recipe
    • Python, where needed
    Include the formula or relevant screenshot at the end.

Q4. Data Preprocessing (Up to 10 Steps)
    For each step, describe what you did and why it was necessary. Add Dataiku/code
    snippets or screenshots wherever applicable at the end of this block (Q4).
    Possible steps include handling missing values, scaling, encoding, filtering,
    transformation, etc.
Q5. Hypotheses Formulation
    For each hypothesis, provide:
    • Hypothesis statement
    • How you arrived at it (pivots, visualizations, domain knowledge, literature)
    • Four-dimensional reasoning: 
        variable, hypothesis, data availability, data quality.

Q6. Model Building Process
    Describe your modeling approach (logistic regression, decision tree or both). 
    Explain your training/testing strategy, number of iterations, tuning approach, or variable selection logic. 
    Mention any changes made to independent variables or encoding.
    Present model output screenshots and extra ones separately in the appendix.

Q7. Model Interpretation (Business and Applied Perspective)
    Convert statistical outcomes into business meaning. 
    Explain what each significant variable implies in the real-world Airbnb context. 
    List up to 10 key insights connecting model outputs to Airbnb strategy or decision-making.

Q8. Critical Conclusions & Automation/Product Development
    Maximum three paragraphs:
    • Critical analysis: limitations, data issues, model weaknesses.
    • Improvements: what could be enhanced in future iterations.
    • Productization: how the model could evolve into an automated dashboard or recommender.
    (Maybe develop a prototype also)

Q9. Proposed Additional Data Science Use Case (implementation is not needed)
    Propose one additional Airbnb-related data science use case, 
    other than predicting whether a listing is successful.
    
    <!-- You are not required to build or execute this use case. -->
    Briefly explain:
    • Use case: What problem would you solve?
    • Business value: Why would this be useful?
    • User/stakeholder: Who would benefit from the solution?
    • Data required: Which existing Airbnb variables or additional data would be
    needed?
    • Possible analytical approach: What type of analysis or model could potentially
    be used?
    • Expected output: What would the final output look like?
    
    Marking Criteria
    Component Weight Description
    Domain knowledge & initial research
    
    25% Includes problem setup, dependent variable
    logic, and justification of formula.
    Data processing & feature
    engineering
   
    25% Quality of preprocessing, transformations,
    and rationale behind feature construction.
    Model building &
    algorithm implementation
    
    25% Suitability of algorithm, training/testing rigor,
    evaluation strategy, reproducibility.
    Interpretation & lifecycle
    closure
    
    25% Translation of results to business insights,
    discussion of limitations, and future
    applications.