Feature: As a user
  I want to be able to see, edit and sort by tags of scrapers
  So that I can find interesting scrapers easily and so I can tag my scrapers
  so that others can find them

  Scenario: I can click on a tag while on the homepage
    Given the "test_scraper" has the tag "testalicious"
    And I am on the home page
    When I click the "testalicious" button 
    Then I should be on the testalicious tag page

