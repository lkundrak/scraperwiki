Feature: As a vault owner
  I want to manage the members of my vault
  So that I can choose who can access my vault.

  Scenario: A vault owner can add a person
    Given I am a "Corporate" user
    And I have a vault
    And I am on the vaults page
    When I click the vault members button
    And I click the "Add another user" button
    And I type "subject" into the username box
    And I click the "Add!" button
    Then I should see "subject"
    And I should see "2 members can access this vault"

