import type { MouseEvent } from 'react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import TeamFlag from './TeamFlag'
import { getTeamByName, getTeamDetailPath } from '../utils/navigation'

type FlagSize = 'sm' | 'md' | 'lg' | 'xl'

interface TeamFlagLinkProps {
  teamName: string
  flagCode?: string
  size?: FlagSize
  className?: string
  showName?: boolean
  nameClassName?: string
  reverse?: boolean
}

export default function TeamFlagLink({
  teamName,
  flagCode,
  size = 'md',
  className,
  showName = false,
  nameClassName,
  reverse = false,
}: TeamFlagLinkProps) {
  const team = getTeamByName(teamName)
  const flag = <TeamFlag flagCode={flagCode || team?.flagCode} teamName={teamName} size={size} />

  if (!team) return flag

  const handleClick = (event: MouseEvent<HTMLAnchorElement>) => {
    event.stopPropagation()
  }

  return (
    <Link
      to={getTeamDetailPath(teamName)}
      onClick={handleClick}
      aria-label={`查看${team.name}球队信息`}
      title={`查看${team.name}球队信息`}
      className={clsx(
        'inline-flex min-w-0 items-center gap-1.5 rounded-lg outline-none transition hover:scale-105 focus-visible:ring-4 focus-visible:ring-blue-500/20',
        reverse && 'flex-row-reverse',
        className
      )}
    >
      {flag}
      {showName && (
        <span className={clsx('min-w-0 truncate font-black text-slate-900', nameClassName)}>
          {team.name}
        </span>
      )}
    </Link>
  )
}
