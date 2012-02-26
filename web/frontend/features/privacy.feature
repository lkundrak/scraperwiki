Feature: As a scraper owner
  I want the privacy settings panel to clearly show that I can
  upgrade my account to put the scraper into a private vault
  So that I know about vaults and how to put my scraper in one

  Scenario: I can edit the scraper privacy settings
    Given I am a "Free" user
    And I visit my scraper's overview page
    When I click the privacy button
    Then I should see the privacy panel
    And I should see the button to change the privacy settings

  Scenario: I can see the upgrade button (Free user)
    Given I am a "Free" user
    And the "Self Service Vaults" feature exists
    And I have the "Self Service Vaults" feature enabled
    And I visit my scraper's overview page
    When I click the privacy button
    And I click the change privacy button
    Then I should see the "Upgrade to activate" link

  # Picking Business as an example of a paid-up user.
  Scenario: I can't see the upgrade button (Business user)
    Given I am a "Business" user
    And the "Self Service Vaults" feature exists
    And I have the "Self Service Vaults" feature enabled
    And I visit my scraper's overview page
    When I click the privacy button
    And I click the change privacy button
    Then I should not see the "Upgrade to activate" link

  # No need to test anonymous users, since they can't own a scraper
  # and, therefore, can't edit a scraper's privacy details.