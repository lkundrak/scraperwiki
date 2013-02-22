Feature: As a non logged-in user
  I want to discover that I need to sign in if I want to buy a Premium Account
  So that I know what to do to get a Premium Account.

  Scenario: I am told to sign in to buy a Premium Account
    Given I am not logged in
    When I visit the pricing page
    Then I should not see "Buy now"
    And I should see "Please log in or sign up to buy"
