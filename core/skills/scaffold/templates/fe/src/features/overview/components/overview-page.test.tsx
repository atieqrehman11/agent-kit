import { render, screen } from '@testing-library/react'

import { APP_NAME } from '@/app/app-info'

import { OverviewPage } from './overview-page'

describe('OverviewPage', () => {
  it('renders the app name as the page heading', () => {
    render(<OverviewPage />)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(APP_NAME)
  })
})
