Feature: As a business or corporate account holder
  I want to create new vaults from my Vaults page
  So that I can partition my work into different private projects

  Scenario: I can see the 'new vault' button (business user)
    Given I am a "Business" user
    When I visit the vaults page
    Then I should see the "Create a new vault" button

  Scenario: I can see the 'new vault' button (corporate user)
    Given I am a "Corporate" user
    When I visit the vaults page
    Then I should see the "Create a new vault" button

  Scenario: I can create a new vault (business user)
    Given I am a "Business" user
    When I visit the vaults page
    And I click the "Create a new vault" button
    Then I should see a new empty vault

  Scenario: I can create a new vault (corporate user)
    Given I am a "Corporate" user
    When I visit the vaults page
    And I click the "Create a new vault" button
    Then I should see a new empty vault

  Scenario: I can't see the 'new vault' button if I have 5 vaults (business user)
    Given I am a "Business" user
    And I have 5 vaults
    When I visit the vaults page
    Then I should not see the "Create a new vault" button
    And I should see the "Upgrade to create more vaults" button

  Scenario: I can't see the 'new vault' button if I have a vault (individual user)
    Given I am a "Individual" user
    And I have a vault
    When I visit the vaults page
    Then I should not see the "Create a new vault" button
    And I should see the "Upgrade to create more vaults" button

  Scenario: I can't sneakily create a new vault if I have 5 vaults (business user)
    Given I am a "Business" user
    And I have 5 vaults
    When I visit the new vault page
    Then I should not see a new empty vault

  Scenario: I can't sneakily create a new vault if I have a vault (individual user)
    Given I am a "Individual" user
    And I have a vault
    When I visit the new vault page
    Then I should not see a new empty vault
    
  Scenario: My vault can't have more than one member (individual user)
    Given I am a "Individual" user
    And I have a vault
    When I visit the vaults page
    When I click the "member" button
    Then I should not see the "Add another user" button
    And I should see the "Upgrade to add more users" button

  Scenario: [WE DON'T ACTUALLY TEST THAT] I can't sneakily add more than one member to my vault (individual user)
    Given I am a "Individual" user
    And I have a vault
    When I make an AJAX request to the endpoint "/vaults/{vaultid}/adduser/{userid}/"
    Then I should not be successful
