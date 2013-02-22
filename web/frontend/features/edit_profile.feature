Feature: Edit Profile Page

  Scenario: I see my API key if I'm a premium account holder
    Given I am an "Individual" user
    When I visit the edit profile page
    Then I should see the API key

  Scenario: I don't see my API key if I'm a free user
    Given I am a "Free" user
    When I visit the edit profile page
    Then I should not see the API key
