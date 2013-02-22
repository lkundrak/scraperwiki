Feature: As a person who writes code on ScraperWiki
  I want to schedule my code to run automatically
  So that I can gather data regularly without thinking about it.

  Scenario: I can see my scraper's schedule
    Given I am a "Business" user
    And I visit my scraper's overview page
    Then I should see the scheduling panel
    And I should see the button to edit the schedule

  Scenario: I can set one of my scrapers to run daily
    Given I am a "Business" user
    And I visit my scraper's overview page
    When I click the "Edit" button in the scheduling panel
    Then I should see the following scheduling options:
      | Don't schedule  |
      | Run every month |
      | Run every week  |
      | Run every day   |
      | Run every hour  |

  Scenario: If I have a Business account then I can set my scraper to run hourly
    Given I am a "Business" user
    And I visit my scraper's overview page
    When I click the "Edit" button in the scheduling panel
    And I click the "Run every hour" schedule option
    Then the scraper should be set to "Runs every hour"

  Scenario: If I have a Corporate account then I can set my scraper to run hourly
    Given I am a "Corporate" user
    And I visit my scraper's overview page
    When I click the "Edit" button in the scheduling panel
    And I click the "Run every hour" schedule option
    Then the scraper should be set to "Runs every hour"

  Scenario: If I have an Individual account then I am told to upgrade to run my scraper hourly
    Given I am an "Individual" user
    And I visit my scraper's overview page
    When I click the "Edit" button in the scheduling panel
    And I should see "Upgrade to activate" 

  Scenario: If I have a Free account then I am told to upgrade to run my scraper hourly
    Given I am a "Free" user
    And I visit my scraper's overview page
    When I click the "Edit" button in the scheduling panel
    And I should see "Upgrade to activate"

   # TODO: Scenario for NOT logged in
