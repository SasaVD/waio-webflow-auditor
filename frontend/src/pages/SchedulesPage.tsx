import { useNavigate } from 'react-router';
import { ScheduleManager } from '../components/ScheduleManager';

export function SchedulesPage() {
  const navigate = useNavigate();
  return <ScheduleManager onBack={() => navigate('/')} />;
}
