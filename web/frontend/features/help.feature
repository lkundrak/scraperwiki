Feature: As a ScraperWiki user, I want to be able to get help when I need it

  Scenario: I should see a link to the status page in the Need Help? box
    When I visit the help page
    Then I should see the "status page" link in the need help box

