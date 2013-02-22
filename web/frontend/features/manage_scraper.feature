Feature: As a user
  I want to be able to create and manage my scrapers
  So that I can start writing and running my code

   Scenario: I can create a scraper if I'm logged in
    Given I am a "Free" user
    And I am on the home page
    And I click the "New Scraper" button 
    And I choose to write my scraper in "Python"
    Then I should be on the python scraper code editing page

   Scenario: I can save a scraper if I'm logged in
    Given I am a "Free" user
    And I create a scraper
    When I save the scraper as "Testing" 
    Then I should be on my "Testing" scraper page

   Scenario: I can delete a scraper
    Given I am a "Free" user
    And I visit my scraper's overview page
    When I click the "Delete Scraper" button
    Then I should be on my profile page

