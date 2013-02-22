Feature: As a salesperson, I want to invite people to a vault by email
  (when they don't have an account on scraperwiki.com) -
  so that they can create an account and see the vault instantly.

  Scenario: A vault owner can invite a person
    Given I am a "Corporate" user
    And I have a vault
    And I am on the vaults page
    When I click the vault members button
    And I click the "Add another user" button
    And I type "t.test@testersonandsons.com" into the username box
    And I click the "Add!" button
    Then an invitation email gets sent to "t.test@testersonandsons.com"
    And I should see "Invitation sent!"

  Scenario: An invite takes one to the sign up page
    Given I have been invited to ScraperWiki
    And there is a sign up link in the invitation email
    When I go to the invitation link in the email
    Then I should be on the sign up page
    And I should see the vault name
    And I should see my email already filled in

  Scenario: An invited person can access the vault after sign up
    Given I have been invited to ScraperWiki
    When I sign up
    Then I should be on the vaults page
    And I should have access to the vault I was invited to
    And the vault owner has been emailed

  Scenario: An invited person messes up their sign up
    Given I have been invited to ScraperWiki
    When I mess my sign up
    Then I should be on the login page
    And I should see the vault name
    And I should see my email already filled in

  Scenario: I try to invite someone who is already a member
    Given I am a "Corporate" user
    And I have a vault
    And I am on the vaults page
    When I click the vault members button
    And I click the "Add another user" button
    And I type "test@example.com" into the username box
    And I click the "Add!" button
    Then I should see "is already a member of this vault"

  Scenario: I try to invite an existing ScraperWiki user
    Given I am a "Corporate" user
    And I have a vault
    And I am on the vaults page
    When I click the vault members button
    And I click the "Add another user" button
    And I type "test+subject@example.com" into the username box
    And I click the "Add!" button
    # 'subject' is the existing ScraperWiki user for test+subject@
    Then I should see "(subject)"
    
